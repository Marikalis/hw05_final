import shutil

from django.core.cache import cache
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import Client, TestCase

from posts.models import Follow, Group, Post, User
from posts.settings import PAGE_SIZE

INDEX = reverse('index')
FOLLOW_INDEX = reverse('follow_index')
NEW_POST = reverse('new_post')
DESCRIPTION = 'Тестовое описание'
USERNAME = 'Test_lisa'
ANOTHER_USERNAME = 'Mysinka'
GROUP_WITHOUT_POST_SLAG = 'test-slug-empty'
GROUP_WITH_POST_SLAG = 'test-slug'
PROFILE = reverse(
    'profile',
    kwargs={'username': USERNAME}
)
GROUP_WITH_POSTS = reverse(
    'group_posts',
    kwargs={'slug': GROUP_WITH_POST_SLAG}
)
GROUP_WITHOUT_POSTS = reverse(
    'group_posts',
    kwargs={'slug': GROUP_WITHOUT_POST_SLAG}
)
FOLLOW = reverse(
    'profile_follow',
    kwargs={'username': ANOTHER_USERNAME}
)
UNFOLLOW = reverse(
    'profile_unfollow',
    kwargs={'username': ANOTHER_USERNAME}
)
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


class PagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_with_post = Group.objects.create(
            title='Группа с постом',
            description=DESCRIPTION,
            slug=GROUP_WITH_POST_SLAG
        )
        cls.group_without_post = Group.objects.create(
            title='Группа без поста',
            description=DESCRIPTION,
            slug=GROUP_WITHOUT_POST_SLAG
        )
        cls.user = User.objects.create_user(username=USERNAME)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.guest_client = Client()
        cls.uploaded_file = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group_with_post,
            image=cls.uploaded_file
        )
        cls.another_user = User.objects.create_user(username=ANOTHER_USERNAME)
        cls.another_authorized_client = Client()
        cls.another_authorized_client.force_login(cls.another_user)
        cls.VIEW_POST = reverse(
            'post',
            kwargs={
                'username': cls.post.author.username,
                'post_id': cls.post.id
            }
        )
        cls.POST_EDIT = reverse(
            'post_edit',
            kwargs={
                'username': cls.post.author.username,
                'post_id': cls.post.id
            }
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_posts_correct_context(self):
        """Шаблоны сформированы с правильным контекстом."""
        Follow.objects.create(
            user=self.another_user,
            author=self.user
        )
        urls_posts = [
            [self.another_authorized_client, INDEX],
            [self.another_authorized_client, GROUP_WITH_POSTS],
            [self.another_authorized_client, PROFILE],
            [self.another_authorized_client, FOLLOW_INDEX],
        ]
        for client, url in urls_posts:
            with self.subTest(url=url):
                posts = client.get(url).context['page']
                self.assertEqual(len(posts), 1)
                self.assertPostsEqual(posts[0], self.post)

    def test_view_post_correct_context(self):
        """Шаблон view_post сформирован с правильным контекстом."""
        urls = [
            self.VIEW_POST,
        ]
        for url in urls:
            post = self.authorized_client.get(url).context['post']
            self.assertPostsEqual(post, self.post)

    def assertPostsEqual(self, post1, post2):
        self.assertEqual(post1.text, post2.text)
        self.assertEqual(post1.group, post2.group)
        self.assertEqual(post1.author, post2.author)
        self.assertEqual(post1.image, post2.image)

    def test_group_show_correct_context(self):
        """Шаблон group_posts сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            GROUP_WITH_POSTS
        )
        group = response.context['group']
        self.assertEqual(group.title, self.group_with_post.title)
        self.assertEqual(group.slug, self.group_with_post.slug)
        self.assertEqual(group.description, self.group_with_post.description)

    def test_author_correct_context(self):
        """Шаблон поста и профайла сформированы с правильным контекстом."""
        urls = [
            self.VIEW_POST,
            PROFILE
        ]
        for url in urls:
            with self.subTest(url=url):
                author = self.authorized_client.get(url).context['author']
                self.assertEqual(author, self.user)

    def test_new_post_with_group_doesnt_shown_on_other_group(self):
        response = self.authorized_client.get(
            GROUP_WITHOUT_POSTS
        )
        self.assertNotIn(self.post, response.context['page'])


SECOND_PAGE_ITEMS_COUNT = 1
ITEMS_COUNT = PAGE_SIZE + SECOND_PAGE_ITEMS_COUNT


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = User.objects.create_user(username='testuser')
        cls.guest_client = Client()
        for index in range(ITEMS_COUNT):
            note = f"запись номер {index} "
            Post.objects.create(
                text=note,
                author=user
            )

    def test_first_page_content(self):
        response = self.client.get(INDEX)
        self.assertEqual(
            len(response.context.get('page').object_list),
            PAGE_SIZE
        )

    def test_second_page_content(self):
        response = self.client.get(INDEX + '?page=2')
        self.assertEqual(
            len(response.context.get('page').object_list),
            SECOND_PAGE_ITEMS_COUNT
        )


class CacheViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        post_note = 'Создаем пост'
        Post.objects.create(
            text=post_note,
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()

    def test_cache_index_pages(self):
        """Проверяем работу кэша главной страницы."""
        first_response = self.client.get(INDEX)
        anoter_post_note = 'Еще один пост'
        Post.objects.create(
            text=anoter_post_note,
            author=self.user
        )
        response_after_post_add = self.client.get(INDEX)
        self.assertEqual(
            first_response.content,
            response_after_post_add.content
        )
        cache.clear()
        response_after_cache_clean = self.client.get(INDEX)
        self.assertNotEqual(
            first_response.content,
            response_after_cache_clean.content
        )


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.another_user = User.objects.create_user(username=ANOTHER_USERNAME)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.guest_client = Client()
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.another_user
        )

    def test_authorized_client_follow(self):
        self.authorized_client.get(
            FOLLOW
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.another_user).exists()
        )

    def test_authorized_client_unfollow(self):
        Follow.objects.create(
            user=self.user,
            author=self.another_user
        )
        self.authorized_client.get(
            UNFOLLOW
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.another_user
            ).exists()
        )

    def test_new_post_doesnt_shown_to_follower(self):
        response = self.authorized_client.get(FOLLOW_INDEX)
        self.assertNotIn(self.post, response.context['page'])
