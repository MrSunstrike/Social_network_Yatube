from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse


class TestURLsAbout(TestCase):
    def setUp(self):
        self.guest_user = Client()

    def test_urls_response(self):
        response_urls = {
            '/about/author/': 'OK',
            '/about/tech/': 'OK'
        }
        for address, status in response_urls.items():
            with self.subTest(address=address):
                response = self.guest_user.get(address)
                self.assertEqual(
                    HTTPStatus(response.status_code).name,
                    status,
                    f'Нет доступа к странице {address}. '
                    f'Код доступа {response.status_code}'
                    f'({HTTPStatus(response.status_code).name})'
                )

    def test_urls_uses_correct_template(self):
        address_templates = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html'
        }
        for address, template in address_templates.items():
            with self.subTest(address=address):
                response = self.guest_user.get(address)
                self.assertTemplateUsed(
                    response,
                    template,
                    f'Адрес {address} использует некорректный шаблон!'
                )

    def test_namespace_uses_correct_template(self):
        namespace_templates = {
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html'
        }
        for namespace, template in namespace_templates.items():
            with self.subTest(namespace=namespace):
                response = self.guest_user.get(namespace)
                self.assertTemplateUsed(response, template)
