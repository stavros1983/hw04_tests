from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.unauthorized_user = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_redirect_unauthorized_user(self):
        """Редирект неавторизованного пользователя"""
        url1 = '/auth/login/?next=/create/'
        url2 = f'/auth/login/?next=/posts/{self.post.id}/edit/'
        pages = {'/create/': url1,
                 f'/posts/{self.post.id}/edit/': url2}
        for page, value in pages.items():
            response = self.unauthorized_user.get(page)
            self.assertRedirects(response, value)

    def test_unauthorized_user_in(self):
        """Проверка доступа для неавторизованного пользователя."""
        field_urls_code = {
            reverse(
                'posts:index'): 200,
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}): 200,
            reverse(
                'posts:group_list',
                kwargs={'slug': 'bad_slug'}): 404,
            reverse(
                'posts:profile',
                kwargs={'username': self.user}): 200,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}): 200,
            reverse(
                'posts:edit',
                kwargs={'post_id': self.post.id}): 302,
            reverse(
                'posts:create'): 302,
            '/unexisting_page/': 404,
        }
        for url, response_code in field_urls_code.items():
            with self.subTest(url=url):
                status_code = self.unauthorized_user.get(url).status_code
                self.assertEqual(status_code, response_code)

    def check_post_info(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)

    def test_forms_show_correct(self):
        """Проверка корректности формы."""
        context = {
            reverse('posts:create'),
            reverse('posts:edit', kwargs={'post_id': self.post.id, }),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(
                    response.context['form'].fields['text'],
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context['form'].fields['group'],
                    forms.fields.ChoiceField)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_info(response.context['page_obj'][0])

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['author'], self.user)
        self.check_post_info(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.check_post_info(response.context['post'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='auth',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.user,
                group=cls.group
            )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_on_first_page = 10
        posts_on_second_page = 3
        url_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_ in url_pages:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_).context.get('page_obj')),
                    posts_on_first_page
                )
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_ + '?page=2').context.get('page_obj')),
                    posts_on_second_page
                )
