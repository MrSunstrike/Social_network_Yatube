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

    def post_check(self, post_context, post_db):
        """
        Проверяет соответствие атрибутов двух объектов Post.

        Аргументы:
            self (TestCase): Экземпляр тестового класса.
            post_context (Post): Объект Post, полученный из контекста.
            post_db (Post): Объект Post, полученный из базы данных.

        Проверяет соответствие следующих атрибутов:
            - text: Текст поста.
            - author.username: Имя пользователя, который написал пост.
            - group.slug: Slug группы, к которой относится пост.
            - image: Наличие картинки в посте.
        """
        self.assertEqual(post_context.text, post_db.text)
        self.assertEqual(post_context.author.username, post_db.author.username)
        self.assertEqual(post_context.group.slug, post_db.group.slug)
        if post_db.image:
            self.assertTrue(post_context.image)

    def test_pages_uses_correct_template(self):
        """
        Проверяет корректность использования шаблонов на страницах.

        Для каждой страницы, указанной в словаре urls_names_list, делается
        запрос и проверяется, что на странице используется правильный шаблон.
        """
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
        """
        Проверяет корректность работы пагинаторов на страницах index,
        group_posts и profile.

        Создаются 15 постов и заполняются списки с количеством постов на
        страницах для каждой страницы, на которой используется пагинатор. Для
        каждой страницы делается запрос и проверяется корректность количества
        постов на странице и тип объекта Page, возвращаемого контекстом.
        """
        post_list = []
        for i in range(15):
            post = Post(text=f'Запись №{i}',
                        author=self.author,
                        group=self.test_group)
            post_list.append(post)
        Post.objects.bulk_create(post_list)
        all_posts = len(Post.objects.all())
        all_group_posts = len(Post.objects.filter(group=self.test_group))
        posts_on_pages = {
            reverse('posts:index'): POSTS_AMOUNT,
            reverse('posts:index') + '?page=2': all_posts % POSTS_AMOUNT,
            reverse('posts:group_posts',
                    kwargs={'slug': self.test_group.slug}): POSTS_AMOUNT,
            reverse('posts:group_posts',
                    kwargs={'slug': self.test_group.slug}) + '?page=2':
                        all_group_posts % POSTS_AMOUNT,
            reverse('posts:profile',
                    kwargs={'username': self.author.username}): POSTS_AMOUNT,
            reverse('posts:profile',
                    kwargs={'username': self.author.username}) + '?page=2':
                        all_posts % POSTS_AMOUNT,
        }
        for page, posts in posts_on_pages.items():
            with self.subTest(page=page):
                response = self.auth_client.get(page)
                context = response.context['page_obj']
                self.assertIsInstance(context, Page)
                self.assertEqual(posts, len(context))

    def test_post_detail_page_show_correct_context(self):
        """
        Проверяет корректность контекста на странице детального просмотра
        поста.

        Делается запрос на страницу детального просмотра конкретного поста и
        проверяется наличие корректного контекста. Контекст проверяется с
        помощью функции post_check, которая сравнивает поля поста и значения в
        словаре контекста.
        """
        response = self.auth_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post_context = response.context['post']
        self.post_check(post_context, Post.objects.get(id=self.post.id))

    def test_edit_post_page_show_correct_context_get(self):
        """
        Проверяет корректность контекста страницы с формой редактирования
        поста.

        Делается GET-запрос на страницу с формой редактирования поста, и
        проверяются наличие в контексте необходимых данных: содержимого и
        группы поста, а также полей формы. Контекст проверяется на наличие
        нужных полей и их тип с помощью словаря form_fields. Содержимое и
        группа поста проверяются с помощью assertContains.
        """
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
        """
        Проверяет сохранение изменений при отправке формы в 'post_edit'.

        Проверяется, что при отправке формы редактирования поста с новым
        текстом, новой группой и новым изображением, изменения сохраняются в
        базе данных.
        """
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
        """
        Проверяет контекст в представлении 'index'.

        Проверяется, что при запросе списка всех постов, передается
        правильный контекст с информацией о постах на текущей странице.
        """
        response = self.auth_client.get(reverse('posts:index'))
        post_context = response.context['page_obj'][0]
        self.post_check(post_context, Post.objects.get(id=self.post.id))

    def test_context_in_post_group(self):
        """
        Проверяет контекст в представлении 'group_posts'.

        Проверяется, что при запросе списка постов в группе, передается
        правильный контекст с информацией о группе и ее постах.
        """
        response = self.auth_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.test_group.slug}
        ))
        post_context = response.context['page_obj'][0]
        group_response = response.context['group']
        self.post_check(post_context, Post.objects.get(id=self.post.id))
        self.assertEqual(group_response.title, self.post.group.title)
        self.assertEqual(group_response.description,
                         self.post.group.description)
        response = self.auth_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.another_group.slug}
        ))
        self.assertNotContains(response, self.post.text)

    def test_context_in_profile(self):
        """
        Тестирование контекста в представлении 'profile'.

        Проверяется, что при запросе страницы профиля пользователя, передается
        правильный контекст с информацией о постах автора и авторе.
        """
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
        """
        Проверяет создание нового поста через форму в 'post_create',
        проверка редиректа и отображения поста на страницах.
        """
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
        """
        Проверяет возможность оставлять комментарий только авторизованным
        пользователям.

        Проверяется, что неавторизованный пользователь
        перенаправляется на страницу входа, а авторизованный пользователь может
        оставлять комментарии к посту.
        """
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
        """
        Проверяет кэширование на главной странице 'index'.

        Создается тестовый пост и делается запрос на страницу 'index'. Затем
        проверяется, что содержимое ответа сохранено в кэше. Удаление тестового
        поста и повторный запрос к странице 'index' должны вернуть сохраненное
        содержимое из кэша. Очистка кэша и повторный запрос к странице 'index'
        должны вернуть новое содержимое.
        """
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

    def test_create_following(self):
        """
        Проверяет создание подписки на профиль пользователя.

        Осуществляется запрос на подписку на профиль пользователя. Затем
        проверяется, что создана новая запись о подписке в базе данных.
        """
        self.auth_client.get(reverse('posts:profile_follow',
                             kwargs={'username': self.user.username}))
        relation = Follow.objects.filter(author=self.user)
        self.assertEqual(len(relation), 1)  # Норм так проверять?

    def test_delete_following(self):
        """
        Проверяет удаление подписки на профиль пользователя.

        Создается запись о подписке на профиль пользователя. Затем
        осуществляется запрос на отписку от этого профиля. Проверяется, что
        запись о подписке была успешно удалена из базы данных.
        """
        Follow.objects.create(user=self.user, author=self.author)
        self.auth_client.get(reverse('posts:profile_unfollow',
                             kwargs={'username': self.user.username}))
        relation = Follow.objects.filter(author=self.user)
        self.assertEqual(len(relation), 0)

    def test_post_on_follow_page(self):
        """
        Проверяет отображение поста на ленте подписок пользователя.

        Создается запись о подписке на профиль пользователя. Затем создается
        клиент для авторизованного пользователя и делается запрос на страницу
        ленты подписок. Проверяется, что первый пост на странице соответствует
        тому, что был опубликован автором, на которого подписался пользователь.
        """
        Follow.objects.create(user=self.user, author=self.author)
        follower_client = Client()
        follower_client.force_login(self.user)
        response_follower = follower_client.get(reverse('posts:follow_index'))
        context_follower = response_follower.context['page_obj'].object_list[0]
        self.assertEqual(context_follower, self.post)

    def test_post_on_follow_page(self):
        """
        Тестирование отображения постов на ленте подписок пользователя.

        Делается запрос на страницу ленты подписок для пользователя, который не
        подписан ни на один профиль. Проверяется, что на странице нет никаких
        постов.
        """
        response_another = self.auth_client.get(reverse('posts:follow_index'))
        if len(response_another.context['page_obj']) > 0:
            context_another = response_another.context['page_obj']
            post_context = context_another.object_list[0]
            self.assertNotEqual(post_context, self.post)
