from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post, User


INDEX_URL = reverse('posts:index')
SLUG = 'test-slug'
GROUP_URL = reverse('posts:group_list', kwargs={'slug': SLUG})
USER = 'TestAuthor'
ANOTHER_USER = 'TestName'
PROFILE_URL = reverse('posts:profile', kwargs={'username': USER})
POST_CREATE_URL = reverse('posts:post_create')
LOGIN_CREATE = reverse('users:login') + '?next=' + POST_CREATE_URL
ERROR_404 = '/whatisthis/'
FOLLOW_INDEX_URL = reverse('posts:follow_index')
FOLLOW_URL = reverse('posts:profile_follow', kwargs={'username': USER})
UNFOLLOW_URL = reverse('posts:profile_unfollow', kwargs={'username': USER})


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=ANOTHER_USER)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='TestText',
            author=User.objects.create(username=USER),
            group=cls.group,
        )
        cls.guest = Client()
        cls.logged_user = Client()
        cls.logged_user.force_login(cls.user)
        cls.author = Client()
        cls.author.force_login(cls.post.author)
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id})
        cls.POST_EDIT_URL = reverse(
            'posts:post_edit', kwargs={'post_id': cls.post.id})
        cls.LOGIN_EDIT = reverse('users:login') + '?next=' + cls.POST_EDIT_URL
        cls.LOGIN_FOLLOW = reverse(
            'users:login') + '?next=' + PROFILE_URL + 'follow/'
        cls.LOGIN_UNFOLLOW = reverse(
            'users:login') + '?next=' + PROFILE_URL + 'unfollow/'

    def test_pages_urls(self):
        """Проверяем доступность URL"""
        urls = [
            [INDEX_URL, 200, self.guest],
            [GROUP_URL, 200, self.guest],
            [PROFILE_URL, 200, self.guest],
            [self.POST_DETAIL_URL, 200, self.logged_user],
            [self.POST_EDIT_URL, 200, self.author],
            [self.POST_EDIT_URL, 302, self.guest],
            [self.POST_EDIT_URL, 302, self.logged_user],
            [POST_CREATE_URL, 200, self.logged_user],
            [POST_CREATE_URL, 302, self.guest],
            [FOLLOW_INDEX_URL, 200, self.logged_user],
            [FOLLOW_INDEX_URL, 200, self.author],
            [FOLLOW_INDEX_URL, 302, self.guest],
            [FOLLOW_URL, 302, self.logged_user],
            [FOLLOW_URL, 302, self.guest],
            [FOLLOW_URL, 302, self.author],
            [UNFOLLOW_URL, 302, self.logged_user],
            [UNFOLLOW_URL, 302, self.guest],
            [ERROR_404, 404, self.logged_user]
        ]
        for url, code, client in urls:
            with self.subTest(code=code, url=url):
                self.assertEqual(client.get(url).status_code, code)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        template_url_names = [
            [INDEX_URL, 'posts/index.html', self.logged_user],
            [GROUP_URL, 'posts/group_list.html', self.logged_user],
            [PROFILE_URL, 'posts/profile.html', self.logged_user],
            [self.POST_DETAIL_URL, 'posts/post_detail.html', self.logged_user],
            [POST_CREATE_URL, 'posts/create_post.html', self.logged_user],
            [self.POST_EDIT_URL, 'posts/create_post.html', self.author],
            [ERROR_404, 'core/404.html', self.logged_user],
            [FOLLOW_INDEX_URL, 'posts/follow.html', self.logged_user]

        ]
        for name, template, client in template_url_names:
            with self.subTest(name=name):
                self.assertTemplateUsed(client.get(name), template)

    def test_urls_redirects(self):
        """Проверка редиректов"""
        urls = [
            [self.POST_EDIT_URL, self.POST_DETAIL_URL, self.logged_user],
            [POST_CREATE_URL, LOGIN_CREATE, self.guest],
            [self.POST_EDIT_URL, self.LOGIN_EDIT, self.guest],
            [FOLLOW_URL, PROFILE_URL, self.logged_user],
            [UNFOLLOW_URL, PROFILE_URL, self.logged_user],
            [FOLLOW_URL, self.LOGIN_FOLLOW, self.guest],
            [UNFOLLOW_URL, self.LOGIN_UNFOLLOW, self.guest]

        ]
        for name, redirect, client in urls:
            with self.subTest(name=name, redirect=redirect):
                self.assertRedirects(client.get(name, follow=True), redirect)
