from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class TestsCreateAndEditForm(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='Author')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.test_group = Group.objects.create(
            title='Группа 1',
            slug='group_1',
            description='Первая тестовая группа'
        )
        cls.test_post = Post.objects.create(
            text='Текст первого тестового поста',
            group=cls.test_group,
            author=cls.author
        )

    def test_create_post(self):
        '''Проверка работы создания поста'''
        test_data = {
            'text': 'Текст второго тестового поста',
            'group': self.test_group.id
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=test_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(
            Post.objects.count(),
            2
        )

    def test_edit_post(self):
        '''Проверка работы изменения поста'''
        change_str = 'Измененная строка'
        test_data = {
            'text': change_str,
            'group': ''
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data=test_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': 1})
        )
        self.assertEqual(
            Post.objects.get(id=1).text,
            change_str
        )
        self.assertIsNone(
            Post.objects.get(id=1).group
        )
