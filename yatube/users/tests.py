from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class UsersURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='Tester',
            email='test@test.test',
            password='testpass'
        )
        cls.uidb64 = urlsafe_base64_encode(force_bytes(cls.user.pk))
        cls.token = default_token_generator.make_token(cls.user)

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(self.user)

    def test_urls_response_for_guest(self):
        """
        Проверка доступов у гостевого пользователя к страницам приложения
        users
        """
        response_urls = {
            '/auth/logout/': 'OK',
            '/auth/login/': 'OK',
            '/auth/signup/': 'OK',
            '/auth/password_reset/done/': 'OK',
            '/auth/reset/password_reset': 'OK',
            '/auth/password_change/done/': 'FOUND',
            '/auth/password_change/': 'FOUND',
            '/auth/reset/done/': 'OK'
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
                        ['/auth/login/?next=/auth/password_change/',
                         '/auth/login/?next=/auth/password_change/done/'],
                        f'У неавторизованного пользователя некорректное '
                        f'перенаправление по адресу "{address}"! '
                        f'Ожидался переход на один из адресов: '
                        f'/auth/login/?next=/auth/password_change/, '
                        f'или /auth/login/?next=/auth/password_change/done'
                        f'а получен переход на {response["Location"]}'
                    )

    def test_urls_response_for_auth(self):
        """
        Проверка доступов у авторизованного пользователя к страницам
        приложения users
        """
        response_urls = {
            '/auth/logout/': 'OK',
            '/auth/login/': 'OK',
            '/auth/signup/': 'OK',
            '/auth/password_reset/done/': 'OK',
            '/auth/reset/password_reset': 'OK',
            '/auth/password_change/done/': 'OK',
            '/auth/password_change/': 'OK',
            '/auth/reset/done/': 'OK'
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                self.auth_client.login(username='Tester', password='testpass')
                response = self.auth_client.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code).name,
                    status,
                    'У авторизованного пользователя некорректный доступ '
                    f'по адресу "{address}"! Должен быть {status}, а '
                    f'получен {HTTPStatus(response.status_code).name}'
                )
                if status == 'FOUND':
                    self.assertIn(
                        response['Location'],
                        ['/auth/login/?next=/auth/password_change/',
                         '/auth/login/?next=/auth/password_change/done/'],
                        f'У авторизованного пользователя некорректное '
                        f'перенаправление по адресу "{address}"! '
                        f'Ожидался переход на один из адресов: '
                        f'/auth/login/?next=/auth/password_change/, '
                        f'или /auth/login/?next=/auth/password_change/done'
                        f'а получен переход на {response["Location"]}'
                    )

    def test_urls_uses_correct_template(self):
        '''Проверка на возвращение корректного шаблона при запросе'''
        address_templates = {
            '/auth/logout/': 'users/logged_out.html',
            '/auth/login/': 'users/login.html',
            '/auth/signup/': 'users/signup.html',
            '/auth/password_reset/done/': 'users/password_reset_done.html',
            '/auth/reset/password_reset': 'users/password_reset_form.html',
            '/auth/password_change/done/': 'users/password_change_done.html',
            '/auth/password_change/': 'users/password_change_form.html',
            '/auth/reset/done/': 'users/password_reset_complete.html',
            f'/auth/reset/{UsersURLTests.uidb64}/{UsersURLTests.token}/':
            'users/password_reset_confirm.html'
        }
        for address, template in address_templates.items():
            with self.subTest(address):
                self.auth_client.login(username='Tester', password='testpass')
                response = self.auth_client.get(address, follow=True)
                self.assertTemplateUsed(
                    response,
                    template,
                    f'При переходе на {address}, подгружается неккоректный '
                    'шаблон'
                )

    def test_namespace_uses_correct_url(self):
        '''Проверка соответствия шаблонов именам адресов в tests'''
        namespace_template_dict = {
            reverse('users:logout'): 'users/logged_out.html',
            reverse('users:login'): 'users/login.html',
            reverse('users:signup'): 'users/signup.html',
            reverse('users:password_reset_done'):
            'users/password_reset_done.html',
            reverse('users:password_reset_form'):
            'users/password_reset_form.html',
            reverse('users:password_change_done'):
            'users/password_change_done.html',
            reverse('users:password_change_form'):
            'users/password_change_form.html',
            reverse('users:password_reset_complete'):
            'users/password_reset_complete.html',
            reverse('users:password_reset_confirm',
                    kwargs={'uidb64': UsersURLTests.uidb64,
                            'token': UsersURLTests.token}):
            'users/password_reset_confirm.html'
        }
        for namespace, template in namespace_template_dict.items():
            with self.subTest(namespace):
                self.auth_client.login(username='Tester', password='testpass')
                response = self.auth_client.get(namespace, follow=True)
                self.assertTemplateUsed(
                    response,
                    template,
                    f'При переходе на {namespace}, подгружается неккоректный '
                    'шаблон'
                )

    def test_form_on_signup(self):
        '''Проверяем, что на страничку передается форма регистрации'''
        response = self.auth_client.get(reverse('users:signup'))
        form = response.context['form']
        self.assertTrue(isinstance(form, UserCreationForm))

    def test_form_is_create_new_user(self):
        '''Проверяем, что форма регистрации создает нового пользователя'''
        test_data = {
            'username': 'Tester2',
            'email': 'test2@test.test',
            'password1': 'Testpass2!',
            'password2': 'Testpass2!'
        }
        response = self.auth_client.post(
            reverse('users:signup'),
            data=test_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:index')
        )
        self.assertTrue(User.objects.get(username='Tester2'))
