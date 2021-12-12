import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User

POST_CREATE_URL = reverse('posts:post_create')
USER = 'TestAuthor'
PROFILE_URL = reverse('posts:profile', kwargs={'username': USER})
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


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
            author=User.objects.create(username=USER),
            group=cls.group,
        )
        cls.POST_EDIT_URL = reverse(
            'posts:post_edit', kwargs={'post_id': cls.post.id})
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id})

    def setUp(self):
        self.guest = Client()
        self.author = Client()
        self.author.force_login(self.post.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post_with_group_created_correct(self):
        """Проверка создания поста"""
        posts_before = set(Post.objects.all())
        small_gif = (            
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_fields = {
            'text': 'Текст для теста создания поста',
            'group': self.group.id,
            'image': uploaded,
        }

        response = self.author.post(
            POST_CREATE_URL,
            data=form_fields,
            follow=True
        )
        posts_after = set(Post.objects.all())
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, PROFILE_URL)
        self.assertEqual(len(posts_after), len(posts_before) + 1)
        post = posts_after.difference(posts_before).pop()
        self.assertEqual(post.text, form_fields['text'])
        self.assertEqual(post.group.id, form_fields['group'])
        self.assertTrue(post.image).exists()
        self.assertIsNotNone(post.author)

    def test_edit_post_with_group_created_correct(self):
        """Проверка редактирования поста"""
        form_fields = {
            'text': 'Текст для теста редактирования',
            'group': self.another_group.id,
        }

        posts_before = Post.objects.count()

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

    def test_post_create_and_edit_post_show_correct_context(self):
        """Шаблон создания и редактирования поста
        сформирован с правильным контекстом."""
        form_fields = [
            ['text',
             forms.fields.CharField,
             POST_CREATE_URL],
            ['group',
             forms.fields.ChoiceField,
             POST_CREATE_URL],
            ['text',
             forms.fields.CharField,
             self.POST_EDIT_URL],
            ['group',
             forms.fields.ChoiceField,
             self.POST_EDIT_URL]
        ]
        for value, expected, url in form_fields:
            with self.subTest(value=value):
                form_field = self.author.get(
                    url).context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
