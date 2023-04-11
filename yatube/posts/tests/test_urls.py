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
        Проверяет доступ неавторизованного пользователя к страницам приложения
        posts.

        Под неавторизованным пользователем выполняет GET-запросы на страницы
        приложения posts.
        Проверяет коды ответов сервера и, при необходимости, перенаправления.

        :return: None
        """
        response_urls = {
            '/': HTTPStatus.OK,
            '/group/test/': HTTPStatus.OK,
            '/profile/Author/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/posts/1/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code),
                    status,
                    'У неавторизованного пользователя некорректный доступ '
                    f'по адресу "{address}"! Должен быть {status}, а '
                    f'получен {HTTPStatus(response.status_code)}'
                )
                if status == HTTPStatus.FOUND:
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
        """
        Проверяет доступ авторизованного пользователя к страницам приложения
        posts.

        Под авторизованным пользователем выполняет GET-запросы на страницы
        приложения posts.
        Проверяет коды ответов сервера и, при необходимости, перенаправления.

        :return: None
        """
        response_urls = {
            '/': HTTPStatus.OK,
            '/group/test/': HTTPStatus.OK,
            '/profile/Author/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/posts/1/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code),
                    status,
                    'У авторизованного пользователя некорректный доступ '
                    f'по адресу "{address}"! Должен быть {status}, а '
                    f'получен {HTTPStatus(response.status_code)}'
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
        """
        Проверяет доступ автора к редактированию поста.

        Под авторизованным пользователем-автором выполняет GET-запрос на
        страницу редактирования своего поста. Проверяет, что сервер возвращает
        успешный ответ (код 200).

        :return: None
        """
        response = self.auth_client_author.get('/posts/1/edit/')
        self.assertEqual(
            HTTPStatus(response.status_code).name,
            'OK',
            'Автор не имеет доступа к редактированию своего поста!'
        )

    def test_urls_uses_correct_template(self):
        """
        Проверяет использование соответствующих шаблонов на страницах
        приложения posts.

        Для каждого URL-адреса в url_template_names проверяется, что
        возвращаемый
        ответ использует правильный шаблон. При несоответствии выводится
        сообщение об ошибке.

        :return: None
        """
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
