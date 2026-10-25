import re
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Category, Comment, Post

User = get_user_model()


class BlogWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            'author', email='author@example.com',
            password='Original-Secret-91',
        )
        cls.reader = User.objects.create_user('reader')
        cls.category = Category.objects.create(
            title='Путешествия', description='О поездках', slug='travel',
        )
        cls.post = Post.objects.create(
            title='Первая поездка', text='Текст публикации',
            author=cls.author, category=cls.category,
            pub_date=timezone.now() - timedelta(days=1),
        )
        cls.other_post = Post.objects.create(
            title='Вторая поездка', text='Другой текст',
            author=cls.reader, category=cls.category,
            pub_date=timezone.now() - timedelta(hours=1),
        )
        cls.comment = Comment.objects.create(
            post=cls.post, author=cls.author, text='Первый комментарий',
        )

    def test_registration_login_logout(self):
        response = self.client.post(reverse('registration'), {
            'username': 'new_user',
            'password1': 'A-New-Secret-7391',
            'password2': 'A-New-Secret-7391',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.get(username='new_user').check_password(
            'A-New-Secret-7391',
        ))
        response = self.client.post(reverse('login'), {
            'username': 'new_user', 'password': 'A-New-Secret-7391',
        })
        self.assertRedirects(response, reverse('blog:index'))
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_edit_uses_current_user_and_ignores_privileges(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse('blog:edit_profile'), {
            'username': 'renamed', 'first_name': 'Анна',
            'last_name': 'Иванова',
            'email': 'new@example.com', 'is_staff': True,
            'is_superuser': True, 'id': self.reader.pk,
        })
        self.assertRedirects(
            response, reverse('blog:profile', args=['renamed']),
        )
        self.author.refresh_from_db()
        self.reader.refresh_from_db()
        self.assertEqual(self.author.email, 'new@example.com')
        self.assertEqual(self.author.get_full_name(), 'Анна Иванова')
        self.assertFalse(self.author.is_staff)
        self.assertFalse(self.author.is_superuser)
        self.assertEqual(self.reader.username, 'reader')

    def test_post_edit_get_keeps_existing_text_and_image_optional(self):
        self.client.force_login(self.author)
        response = self.client.get(
            reverse('blog:edit_post', args=[self.post.pk]),
        )
        form = response.context['form']
        self.assertFalse(form.is_bound)
        self.assertEqual(form['text'].value(), self.post.text)
        self.assertFalse(form.fields['image'].required)
        self.assertTrue(form.fields['category'].required)

    def test_comment_cannot_be_addressed_through_another_post(self):
        self.client.force_login(self.author)
        for name in ('blog:edit_comment', 'blog:delete_comment'):
            url = reverse(name, args=[self.other_post.pk, self.comment.pk])
            for method in ('get', 'post'):
                with self.subTest(name=name, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 404)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, 'Первый комментарий')

    def test_comment_creation_ignores_forged_author_and_post(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse('blog:add_comment', args=[self.post.pk]), {
                'text': 'Новый комментарий', 'author': self.author.pk,
                'post': self.other_post.pk,
            },
        )
        self.assertRedirects(
            response, reverse('blog:post_detail', args=[self.post.pk]),
        )
        comment = Comment.objects.get(text='Новый комментарий')
        self.assertEqual(comment.author, self.reader)
        self.assertEqual(comment.post, self.post)

    def test_hidden_post_cannot_be_read_or_commented_by_visitor(self):
        self.client.force_login(self.reader)
        self.post.is_published = False
        self.post.save()
        response = self.client.get(
            reverse('blog:post_detail', args=[self.post.pk]),
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse('blog:add_comment', args=[self.post.pk]),
            {'text': 'Текст'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.post.comments.count(), 1)

    def test_delete_get_is_confirmation_and_post_deletes(self):
        self.client.force_login(self.author)
        for name, obj, text in (
            ('blog:delete_comment', self.comment, self.comment.text),
            ('blog:delete_post', self.post, self.post.title),
        ):
            args = [self.post.pk]
            if isinstance(obj, Comment):
                args.append(obj.pk)
            url = reverse(name, args=args)
            response = self.client.get(url)
            self.assertContains(response, text)
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
            self.assertEqual(self.client.delete(url).status_code, 405)
        self.client.post(reverse('blog:delete_post', args=[self.post.pk]))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_scheduled_post_becomes_visible_at_publication_time(self):
        publish_at = timezone.now() + timedelta(days=1)
        self.post.pub_date = publish_at
        self.post.save()
        url = reverse('blog:post_detail', args=[self.post.pk])
        with patch('blog.utils.timezone.now', return_value=publish_at):
            self.assertEqual(self.client.get(url).status_code, 200)
        with patch('blog.utils.timezone.now', return_value=(
            publish_at - timedelta(microseconds=1)
        )):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_empty_comment_is_not_saved(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse('blog:add_comment', args=[self.post.pk]), {'text': '   '},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('text', response.context['form'].errors)
        self.assertEqual(self.post.comments.count(), 1)

    @override_settings(DEBUG=False)
    def test_csrf_and_server_error_use_custom_templates(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('login'), {})
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'pages/403csrf.html')
        with patch('blog.views.get_page', side_effect=RuntimeError('test')):
            response = Client(raise_request_exception=False).get('/')
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'pages/500.html')

    def test_password_reset_writes_file_and_changes_password(self):
        with TemporaryDirectory() as directory, self.settings(
            EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
            EMAIL_FILE_PATH=directory,
        ):
            response = self.client.post(reverse('password_reset'), {
                'email': self.author.email,
            })
            self.assertRedirects(response, reverse('password_reset_done'))
            email_files = list(Path(directory).glob('*.log'))
            self.assertEqual(len(email_files), 1)
            message = email_files[0].read_text()
            reset_url = re.search(
                r'http://testserver(/auth/reset/[^\s]+/)', message,
            )
            self.assertIsNotNone(reset_url)
            response = self.client.get(reset_url.group(1), follow=True)
            self.assertEqual(response.status_code, 200)
            url = response.redirect_chain[-1][0]
            response = self.client.post(url, {
                'new_password1': 'Changed-Secret-7391',
                'new_password2': 'Changed-Secret-7391',
            })
            self.assertRedirects(response, reverse('password_reset_complete'))
        self.author.refresh_from_db()
        self.assertTrue(self.author.check_password('Changed-Secret-7391'))
