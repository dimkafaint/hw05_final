import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

POST_CREATE_URL = reverse('posts:post_create')
LOGIN_CREATE = reverse('users:login') + '?next=' + POST_CREATE_URL
USER = 'TestName'
AUTHOR = 'TestAuthor'
PROFILE_URL = reverse('posts:profile', kwargs={'username': USER})
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B')
ANOTHER_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xF0\xF0\xF0\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.another_group = Group.objects.create(
            title='Другая тестовая группа',
            slug='another_test-slug',
            description='Другое тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=User.objects.create(username=AUTHOR),
            group=cls.group,
        )
        cls.user = User.objects.create_user(username=USER)
        cls.guest = Client()
        cls.logged_user = Client()
        cls.logged_user.force_login(cls.user)
        cls.author = Client()
        cls.author.force_login(cls.post.author)
        cls.POST_EDIT_URL = reverse(
            'posts:post_edit', kwargs={'post_id': cls.post.id})
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id})
        cls.COMMENT_URL = reverse(
            'posts:add_comment', kwargs={'post_id': cls.post.id})
        cls.LOGIN_COMMENT = reverse(
            'users:login') + '?next=' + cls.COMMENT_URL

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post_with_group_created_correct(self):
        """Проверка создания поста"""
        posts_before = set(Post.objects.all())
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_fields = {
            'text': 'Текст для теста создания поста',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.logged_user.post(
            POST_CREATE_URL,
            data=form_fields,
            follow=True
        )
        posts_after = set(Post.objects.all())
        post = posts_after.difference(posts_before)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, PROFILE_URL)
        self.assertEqual(len(post), 1)
        post = post.pop()
        self.assertEqual(post.text, form_fields['text'])
        self.assertEqual(post.group.id, form_fields['group'])
        self.assertEqual(post.author, self.user)
        self.assertTrue(post.image)

    def test_post_create_by_anon(self):
        """"Проверка создания поста анонимом"""
        posts_before = set(Post.objects.all())
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_fields = {
            'text': 'Текст для теста создания поста',
            'group': self.group.id,
            'image': uploaded,
        }
        response_anon = self.guest.post(
            POST_CREATE_URL,
            data=form_fields,
            follow=False
        )
        posts_after = set(Post.objects.all())
        self.assertEqual(response_anon.status_code, 302)
        self.assertRedirects(response_anon, LOGIN_CREATE)
        self.assertEqual(len(posts_after.difference(posts_before)), 0)

    def test_edit_post_with_group_created_correct(self):
        """Проверка редактирования поста"""
        posts_before = Post.objects.count()
        reloaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_fields = {
            'text': 'Текст для теста редактирования',
            'group': self.another_group.id,
            'image': reloaded
        }
        response = self.author.post(
            self.POST_EDIT_URL,
            data=form_fields,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(Post.objects.count(), posts_before)
        post = response.context.get('post')
        self.assertEqual(post.text, form_fields['text'])
        self.assertEqual(post.group.id, form_fields['group'])
        self.assertEqual(post.author, self.post.author)
        self.assertTrue(post.image)

    def test_post_create_and_edit_by_anon_and_non_author(self):
        """Проверка редактирования поста анонимом/не автором"""
        posts_before = set(Post.objects.all())
        reloaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_fields = {
            'text': 'Текст для теста редактирования',
            'group': self.another_group.id,
            'image': reloaded
        }
        clients = [self.guest, self.logged_user]
        for client in clients:
            response = client.post(
                self.POST_EDIT_URL,
                data=form_fields,
                follow=False
            )
            posts_after = set(Post.objects.all())
            post = posts_after.pop()
            with self.subTest(client=client):
                self.assertEqual(response.status_code, 302)
                self.assertEqual(len(posts_after.difference(posts_before)), 0)
                self.assertEqual(self.post, post)
                self.assertEqual(self.post.text, post.text)
                self.assertEqual(self.post.group, post.group)
                self.assertEqual(self.post.author, post.author)
                self.assertEqual(self.post.image, post.image)

    def test_post_create_and_edit_post_show_correct_context(self):
        """Шаблон создания и редактирования поста
        сформирован с правильным контекстом."""
        urls = [POST_CREATE_URL, self.POST_EDIT_URL]
        form_fields = [['text', forms.fields.CharField],
                       ['group', forms.fields.ChoiceField],
                       ['image', forms.fields.ImageField]]
        for url in urls:
            form = self.author.get(url)
            for value, expected in form_fields:
                with self.subTest(value=value):
                    form_field = form.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_add_comment_user(self):
        """Проверка добавления комментария пользователем"""
        comments_before = set(Comment.objects.all())
        form_fields = {
            'text': 'Тестовый комментарий'
        }

        response = self.logged_user.post(
            self.COMMENT_URL,
            data=form_fields,
            follow=True
        )
        comments_after = set(Comment.objects.all())
        comment = comments_after.difference(comments_before)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(len(comment), 1)
        comment = comment.pop()
        self.assertEqual(comment.text, form_fields['text'])
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)

    def test_comment_anon(self):
        """Проверка добавления комментария анонимом"""
        comments = set(Comment.objects.all())
        form_fields = {'text': 'TestAnon'}
        response = self.guest.post(
            self.COMMENT_URL,
            data=form_fields,
            follow=True
        )
        comments = set(Comment.objects.all()).difference(comments)
        self.assertRedirects(response, self.LOGIN_COMMENT)
        self.assertFalse(comments)
