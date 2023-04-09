import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post
from ..views import POSTS_AMOUNT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
GIF_EXAMPLE = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
User = get_user_model()


def post_check(self, post_context, post_db):
    '''Функция проверки постов в контексте'''
    self.assertEqual(post_context.text, post_db.text)
    self.assertEqual(post_context.author.username, post_db.author.username)
    self.assertEqual(post_context.group.slug, post_db.group.slug)
    if post_db.image:
        self.assertTrue(post_context.image)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=GIF_EXAMPLE,
            content_type='image/gif'
        )
        cls.author = User.objects.create_user(username='Author')
        cls.user = User.objects.create_user(username='Second')
        cls.test_group = Group.objects.create(
            title='Тест №1',
            slug='1',
            description='Тестовая №1'
        )
        cls.another_group = Group.objects.create(
            title='Тест №2',
            slug='2',
            description='Тестовая №2'
        )
        cls.post = Post.objects.create(text='Запись №1',
                                       group=cls.test_group,
                                       author=cls.author,
                                       image=cls.image)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        urls_names_list = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts',
                    kwargs={'slug': self.test_group.slug}):
            'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.author.username}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
            'posts/create_edit_post.html',
            reverse('posts:post_create'): 'posts/create_edit_post.html'
        }
        for name, template in urls_names_list.items():
            with self.subTest(name=name):
                response = self.auth_client.get(name)
                self.assertTemplateUsed(
                    response,
                    template,
                    f'По адресу {name}, передается некорректный шаблон'
                )

    def test_all_paginators_is_correct(self):
        '''Проверка пагинаторов в index, group_posts и profile'''
        for post in range(25):
            if post % 2 == 0:
                Post.objects.create(
                    text=f'Запись №{post + 2}',
                    author=self.author,
                    group=self.test_group
                )
            else:
                Post.objects.create(
                    text=f'Запись №{post + 2}',
                    author=self.author
                )
        all_posts = len(Post.objects.all())
        all_group_posts = len(Post.objects.filter(group=self.test_group))
        posts_on_pages = {
            reverse('posts:index'): POSTS_AMOUNT,
            reverse('posts:index') + '?page=3': all_posts % POSTS_AMOUNT,
            reverse('posts:group_posts',
                    kwargs={'slug': self.test_group.slug}): POSTS_AMOUNT,
            reverse('posts:group_posts',
                    kwargs={'slug': self.test_group.slug}) + '?page=2':
                        all_group_posts % POSTS_AMOUNT,
            reverse('posts:profile',
                    kwargs={'username': self.author.username}): POSTS_AMOUNT,
            reverse('posts:profile',
                    kwargs={'username': self.author.username}) + '?page=3':
                        all_posts % POSTS_AMOUNT,
        }
        for page, posts in posts_on_pages.items():
            with self.subTest(page=page):
                response = self.auth_client.get(page)
                context = response.context['page_obj']
                self.assertIsInstance(context, Page)
                self.assertEqual(posts, len(context))

    def test_post_detail_page_show_correct_context(self):
        '''Проверка контекстного контента в post_detail'''
        response = self.auth_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post_context = response.context['post']
        post_check(self, post_context, Post.objects.get(id=self.post.id))
        self.assertTrue(post_context.image)

    def test_edit_post_page_show_correct_context_get(self):
        '''Проверка контекстного контента при get-запросе в edit_post'''
        response = self.auth_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for field, type in form_fields.items():
            with self.subTest(field=field):
                self.assertIsInstance(
                    response.context['form'].fields[field], type
                )
        self.assertContains(response, self.post.text)
        self.assertContains(response, self.test_group.title)

    def test_edit_post_page_save_changes(self):
        '''Проверка сохранения изменений при отправке формы в post_edit'''
        text_for_new_post = 'New text for this post'
        group_for_new_post = self.another_group.slug
        upd_image = SimpleUploadedFile(
            name='upd.gif',
            content=GIF_EXAMPLE,
            content_type='image/gif'
        )
        response = self.auth_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data={
                'text': text_for_new_post,
                'group': group_for_new_post,
                'image': upd_image
            },
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Post.objects.get(id=self.post.id).text,
                         text_for_new_post)
        self.assertEqual(Post.objects.get(id=self.post.id).group.slug,
                         group_for_new_post)

    def test_context_in_index(self):
        '''Проверка контекста в index'''
        response = self.auth_client.get(reverse('posts:index'))
        post_context = response.context['page_obj'][0]
        post_check(self, post_context, Post.objects.get(id=self.post.id))
        self.assertTrue(post_context.image)

    def test_context_in_post_group(self):
        '''Проверка контекста в group_post'''
        response = self.auth_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.test_group.slug}
        ))
        post_context = response.context['page_obj'][0]
        group_response = response.context['group']
        post_check(self, post_context, Post.objects.get(id=self.post.id))
        self.assertEqual(group_response.title, self.post.group.title)
        self.assertEqual(group_response.description,
                         self.post.group.description)
        response = self.auth_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.another_group.slug}
        ))
        self.assertNotContains(response, self.post.text)
        self.assertTrue(post_context.image)

    def test_context_in_profile(self):
        '''Проверка контекста в profile'''
        response = self.auth_client.get(reverse('posts:profile',
                                                kwargs={'username':
                                                        self.author.username}))
        post_context = response.context['page_obj'][0]
        self.assertEqual(post_context,
                         Post.objects.filter(author=self.author).first())
        author = response.context['author']
        self.assertEqual(author.username, self.author.username)
        self.assertEqual(author.id, self.author.id)
        self.assertTrue(post_context.image)

    def test_create_post_page_create_new_post(self):
        '''
        Проверка создания поста в post_create, редиректа и его отображения
        на страницах
        '''
        text_for_new_post = 'Text for new post'
        group_for_new_post = self.another_group.id
        uploaded = SimpleUploadedFile(
            name='new_img.gif',
            content=GIF_EXAMPLE,
            content_type='image/gif'
        )
        response = self.auth_client.post(
            reverse('posts:post_create'),
            data={
                'text': text_for_new_post,
                'group': group_for_new_post,
                'image': uploaded
            },
            follow=True
        )
        created_post = Post.objects.filter(text=text_for_new_post).first()
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(created_post.text, text_for_new_post)
        self.assertEqual(created_post.group.title, self.another_group.title)
        self.assertTrue(created_post.image)

        address_list = [
            reverse('posts:index'),
            reverse('posts:group_posts',
                    kwargs={'slug': self.another_group.slug}),
            reverse('posts:profile', kwargs={'username':
                                             self.author.username}),
        ]
        for address in address_list:
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertIn(created_post, response.context['page_obj'])
        response = self.auth_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.test_group.slug}))
        self.assertNotIn(created_post, response.context['page_obj'])

    def test_comment_may_added_only_auth_user(self):
        '''Проверка возможности оставлять комментарий пользователям'''
        text = 'Это тестовый комментарий'
        status_redirects_dict = {
            f'/auth/login/?next=/posts/{self.post.pk}/comment/':
            self.guest_client,
            f'/posts/{self.post.pk}/': self.auth_client
        }
        for address, client in status_redirects_dict.items():
            with self.subTest(client=client):
                response = client.post(
                    reverse('posts:add_comment',
                            kwargs={'post_id': self.post.pk}),
                    data={'text': text}
                )
                self.assertEqual(response['Location'], address)
                if response['Location'] == f'/posts/{self.post.pk}/':
                    response = self.auth_client.get(
                        reverse('posts:post_detail',
                                kwargs={'post_id': self.post.pk})
                    )
                    new_comment = response.context['comments'].first().text
                    self.assertEqual(new_comment, text)

    def test_cached_posts_index(self):
        '''Проверка кэширования постов в index.html'''
        test_post = Post.objects.create(text='Тест кэша', author=self.author)
        response = self.auth_client.get(reverse('posts:index'))
        content = response.content
        test_post.delete()
        cached_responsed = self.auth_client.get(reverse('posts:index'))
        cached_content = cached_responsed.content
        self.assertEqual(content, cached_content)
        cache.clear()
        new_responsed = self.auth_client.get(reverse('posts:index'))
        new_content = new_responsed.content
        self.assertNotEqual(content, new_content)

    def test_create_and_delete_following(self):
        '''Проверка создания и удаления постов'''
        self.auth_client.get(reverse('posts:profile_follow',
                             kwargs={'username': self.user.username}))
        relation = Follow.objects.filter(author=self.user)
        self.assertEqual(len(relation), 1)
        self.auth_client.get(reverse('posts:profile_unfollow',
                             kwargs={'username': self.user.username}))
        relation = Follow.objects.filter(author=self.user)
        self.assertEqual(len(relation), 0)

    def test_post_on_follow_page(self):
        Follow.objects.create(user=self.user, author=self.author)
        follower_client = Client()
        follower_client.force_login(self.user)
        response_follower = follower_client.get(reverse('posts:follow_index'))
        context_follower = response_follower.context['page_obj'].object_list[0]
        self.assertEqual(context_follower, self.post)
        response_another = self.auth_client.get(reverse('posts:follow_index'))
        if len(response_another.context['page_obj']) > 0:
            context_another = response_another.context['page_obj']
            post_context = context_another.object_list[0]
            self.assertNotEqual(post_context, self.post)
