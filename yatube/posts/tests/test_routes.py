from django.test import TestCase
from django.urls import reverse


class TestRoutes(TestCase):
    def test_routes_uses_correct_url(self):
        SLUG, USERNAME, ID = 'slug', 'User', 1
        cases = [
            ['index', None, '/'],
            ['group_list', [SLUG], f'/group/{SLUG}/'],
            ['profile', [USERNAME], f'/profile/{USERNAME}/'],
            ['post_create', None, '/create/'],
            ['post_detail', [ID], f'/posts/{ID}/'],
            ['post_edit', [ID], f'/posts/{ID}/edit/']
        ]
        for name, keys, url in cases:
            with self.subTest(url=url):
                self.assertEqual(reverse(f'posts:{name}', args=keys), url)
