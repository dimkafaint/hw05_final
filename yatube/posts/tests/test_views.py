from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from yatube.settings import PAGINATOR_COUNT
from ..models import Follow, Group, Post, User


INDEX_URL = reverse('posts:index')
SLUG = 'test-slug'
GROUP_URL = reverse('posts:group_list', kwargs={'slug': SLUG})
ANOTHER_SLUG = 'another_test-slug'
ANOTHER_GROUP_URL = reverse('posts:group_list',
                            kwargs={'slug': ANOTHER_SLUG})
USER = 'Testname'
AUTHOR = 'TestAuthor'
PUBLISHER = 'Publisher'
PROFILE_URL = reverse('posts:profile', kwargs={'username': AUTHOR})
FOLLOW_INDEX = reverse('posts:follow_index')
FOLLOW = reverse('posts:profile_follow', kwargs={'username': PUBLISHER})
UNFOLLOW = reverse('posts:profile_unfollow', kwargs={'username': PUBLISHER})


class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USER)
        cls.publisher = User.objects.create_user(username=PUBLISHER)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
            description='Тестовое описание',
        )
        cls.another_group = Group.objects.create(
            title='Другая тестовая группа',
            slug=ANOTHER_SLUG,
            description='Другое тестовое описание',
        )
        cls.post = Post.objects.create(
            text='TestText',
            author=User.objects.create(username=AUTHOR),
            group=cls.group,
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.post.author
        )
        cls.another_follow = Follow.objects.create(
            user=cls.user,
            author=cls.publisher
        )
        cls.guest = Client()
        cls.logged_user = Client()
        cls.logged_user.force_login(cls.user)
        cls.author = Client()
        cls.author.force_login(cls.post.author)
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id})

    def test_post_shows_on_page(self):
        """Пост отображается на странице"""
        page_urls = [
            INDEX_URL,
            GROUP_URL,
            PROFILE_URL,
            self.POST_DETAIL_URL,
            FOLLOW_INDEX
        ]
        for url in page_urls:
            response = self.logged_user.get(url)
            if url == self.POST_DETAIL_URL:
                post = response.context['post']
            else:
                posts = response.context['page_obj']
                self.assertEqual(len(posts), 1)
                post = response.context['page_obj'][0]
            self.assertEqual(self.post.author, post.author)
            self.assertEqual(self.post.group, post.group)
            self.assertEqual(self.post.text, post.text)
            self.assertEqual(self.post.id, post.id)
            self.assertEqual(self.post.image, post.image)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.logged_user.get(GROUP_URL)
        group = response.context.get('group')
        self.assertEqual(self.group, response.context['group'])
        self.assertEqual(self.group.slug, group.slug)
        self.assertEqual(self.group.title, group.title)
        self.assertEqual(self.group.description, group.description)

    def test_post_not_in_another_group(self):
        """Пост не попал в другую группу и ленту подписок"""
        urls = [
            ANOTHER_GROUP_URL,
            FOLLOW_INDEX
        ]
        for url in urls:
            response = self.author.get(url).context['page_obj']
            self.assertNotIn(self.post, response)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.logged_user.get(PROFILE_URL)
        self.assertEqual(self.post.author, response.context['author'])

    def test_cache_index_page(self):
        """Тест кэша"""
        posts_before = self.logged_user.get(INDEX_URL).content
        Post.objects.all().delete()
        posts_after = self.logged_user.get(INDEX_URL).content
        self.assertTrue(posts_before == posts_after)
        cache.clear()
        posts_after_clear_cache = self.logged_user.get(INDEX_URL).content
        self.assertFalse(posts_before == posts_after_clear_cache)

    def test_follow(self):
        """Тест подписки"""
        Follow.objects.all().delete()
        self.logged_user.get(FOLLOW)
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=self.publisher).exists())

    def test_unfollow(self):
        """Тест отписки"""
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=self.publisher).exists())
        self.logged_user.get(UNFOLLOW)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.publisher).exists())


class PostPaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=AUTHOR)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=SLUG,
            description='Тестовое описание',
        )
        cls.posts_count = PAGINATOR_COUNT + 1
        cls.posts = [Post(text=f'Тестовый текст№{id}',
                          author=cls.user,
                          group=cls.group,
                          ) for id in range(cls.posts_count)]
        Post.objects.bulk_create(cls.posts)

    def test_paginator(self):
        """Тестирование пагинатора"""
        urls = [
            [INDEX_URL, PAGINATOR_COUNT],
            [GROUP_URL, PAGINATOR_COUNT],
            [PROFILE_URL, PAGINATOR_COUNT],
            [INDEX_URL + '?page=2', 1],
            [GROUP_URL + '?page=2', 1],
            [PROFILE_URL + '?page=2', 1],
        ]
        for url, count in urls:
            self.assertEqual(len(
                self.client.get(url).context['page_obj']), count)
