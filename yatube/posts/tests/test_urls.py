from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Group.objects.create(
            title='Тест',
            slug='test',
            description='Тестовая группа'
        )
        User.objects.create_user(
            username='Author'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=User.objects.get(username='Author'),
            group=Group.objects.get(slug='test')
        )

    def setUp(self):
        self.guest_client = Client()
        self.author = User.objects.get(username='Author')
        self.user = User.objects.create_user(username='User')
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.auth_client_author = Client()
        self.auth_client_author.force_login(self.author)

    def test_urls_response_for_guest(self):
        """
        Проверка доступов у неавторизованного пользователя к страницам
        приложения posts
        """
        response_urls = {
            '/': 'OK',
            '/group/test/': 'OK',
            '/profile/Author/': 'OK',
            '/posts/1/': 'OK',
            '/posts/1/edit/': 'FOUND',  # Этот отправляет на login
            '/create/': 'FOUND',  # И вот этот. Я что-то забыл?
            '/unexisting_page/': 'NOT_FOUND'
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code).name,
                    status,
                    'У неавторизованного пользователя некорректный доступ '
                    f'по адресу "{address}"! Должен быть {status}, а '
                    f'получен {HTTPStatus(response.status_code).name}'
                )
                if status == 'FOUND':
                    self.assertIn(
                        response['Location'],
                        ['/auth/login/?next=/posts/1/edit/',
                         '/auth/login/?next=/create/'],
                        f'У неавторизованного пользователя некорректное '
                        f'перенаправление по адресу "{address}"! '
                        f'Ожидался переход на один из адресов: '
                        f'/auth/login/?next=/posts/1/edit/, '
                        f'или /auth/login/?next=/create/'
                        f'а получен переход на {response["Location"]}'
                    )

    def test_urls_response_for_auth(self):
        '''
        Проверка доступов у авторизованного пользователя к страницам
        приложения posts
        '''
        response_urls = {
            '/': 'OK',
            '/group/test/': 'OK',
            '/profile/Author/': 'OK',
            '/posts/1/': 'OK',
            '/posts/1/edit/': 'FOUND',
            '/create/': 'OK',
            '/unexisting_page/': 'NOT_FOUND'
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code).name,
                    status,
                    'У авторизованного пользователя некорректный доступ '
                    f'по адресу "{address}"! Должен быть {status}, а '
                    f'получен {HTTPStatus(response.status_code).name}'
                )
                if status == 'FOUND':
                    self.assertEqual(
                        response['Location'],
                        '/posts/1/',
                        f'У авторизованного пользователя некорректное '
                        f'перенаправление по адресу "{address}"! '
                        f'Ожидался переход на /posts/1/, '
                        f'а получен переход на {response["Location"]}'
                    )

    def test_edit_page_response_for_author(self):
        '''Проверка доступа к редактированию поста у автора'''
        response = self.auth_client_author.get('/posts/1/edit/')
        self.assertEqual(
            HTTPStatus(response.status_code).name,
            'OK',
            'Автор не имеет доступа к редактированию своего поста!'
        )

    def test_urls_uses_correct_template(self):
        '''
        Проверка использования соответствующих шаблонов на страницах
        приложения posts
        '''
        url_template_names = {
            '/': 'posts/index.html',
            '/group/test/': 'posts/group_list.html',
            '/profile/Author/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_edit_post.html',
            '/create/': 'posts/create_edit_post.html',
            '/not_found/': 'core/404.html'
        }
        for address, template in url_template_names.items():
            with self.subTest(address=address):
                response = self.auth_client_author.get(address)
                self.assertTemplateUsed(
                    response,
                    template,
                    f'Некорректный шаблон по адресу {address}'
                )
