import shutil
import tempfile

from django import forms

from django.conf import settings
from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from posts.models import Group, Post, User
from posts.settings import SMALL_GIF

INDEX = reverse('index')
NEW_POST = reverse('new_post')
POST_TEXT = 'Тестовый пост'


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.user = User.objects.create_user(username='MarieL')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title='Название',
            description='Описание',
            slug='test-slug'
        )
        cls.group_other = Group.objects.create(
            title='Название другой группы',
            description='Описание другой группы',
            slug='test-other-slug'
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.user,
        )
        cls.uploaded_file = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.EDIT_POST = reverse('post_edit', args=[
            cls.post.author.username, cls.post.id])
        cls.POST = reverse('post', args=[
            cls.post.author.username, cls.post.id])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_before = set(Post.objects.all())
        form_data = {
            'text': POST_TEXT,
            'group': self.group.id,
            'image': self.uploaded_file
        }
        response = self.authorized_client.post(
            NEW_POST,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, INDEX)
        posts_after = set(Post.objects.all())
        list_diff = posts_before ^ posts_after
        self.assertEqual(len(list_diff), 1)
        new_post = list_diff.pop()
        self.assertEqual(new_post.text, POST_TEXT)
        self.assertEqual(new_post.group, self.group)
        self.assertEqual(new_post.author, self.user)
        self.assertEqual(new_post.image, f'posts/{self.uploaded_file.name}')

    def test_post_edit(self):
        """При редактировании поста изменяется запись в базе данных."""
        text_after_edit = 'Тестовый пост после редактирования'
        form_data = {
            'text': text_after_edit,
            'group': self.group_other.id
        }
        response = self.authorized_client.post(
            self.EDIT_POST,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, self.POST)
        post_after_edit = response.context['post']
        self.assertEqual(post_after_edit.text, text_after_edit)
        self.assertEqual(post_after_edit.group, self.group_other)
        self.assertEqual(post_after_edit.author, self.post.author)

    def test_new_post_page_show_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(NEW_POST)
        form_fields = {
            'group': forms.models.ModelChoiceField,
            'text': forms.fields.CharField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
