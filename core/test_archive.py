import json
import shutil

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import Comment, Post, Reaction, Tag


@override_settings(
    ARCHIVE_MODE=True,
    ARCHIVE_OPENED_DATE='2026-01-01',
    ARCHIVE_CLOSED_DATE='2026-09-05',
    ARCHIVE_SITE_URL='https://krine.ca',
)
class ArchiveModeTests(TestCase):
    def setUp(self):
        self.post = Post.objects.create(content='A preserved thought.', post_type='thought', is_flagged=False, is_analyzed=True)
        tag = Tag.objects.create(name='Reflective')
        tag.posts.add(self.post)

    def test_archive_home_is_read_only(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/archive_post_list.html')
        self.assertContains(response, 'CLOSED / READ ONLY')
        self.assertContains(response, 'A preserved thought.')

    def test_flagged_and_unanalyzed_posts_are_hidden(self):
        Post.objects.create(content='Flagged content', is_flagged=True, is_analyzed=True)
        Post.objects.create(content='Pending content', is_flagged=False, is_analyzed=False)
        response = self.client.get('/')
        self.assertNotContains(response, 'Flagged content')
        self.assertNotContains(response, 'Pending content')

    def test_write_methods_fail_closed(self):
        response = self.client.post('/create/', {'content': 'new'})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Post.objects.count(), 1)
        response = self.client.post(f'/post/{self.post.pk}/', {'content': 'comment'})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Comment.objects.count(), 0)

    def test_like_route_cannot_mutate(self):
        response = self.client.get(f'/post/{self.post.pk}/like/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 0)


class ArchiveExportTests(TestCase):
    output_name = '.tmp_archive_test'

    def setUp(self):
        self.output_dir = settings.BASE_DIR / self.output_name
        shutil.rmtree(self.output_dir, ignore_errors=True)
        self.post = Post.objects.create(content='Frozen in amber.', post_type='confession', is_flagged=False, is_analyzed=True)
        Comment.objects.create(post=self.post, content='Still here.')
        Reaction.objects.create(post=self.post, reaction_type=Reaction.LIKE, session_id='archive-test')

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def test_export_builds_static_site_and_manifest(self):
        call_command('export_archive', output=self.output_name, domain='example.com', opened_date='2026-01-01', closed_date='2026-09-05', verbosity=0)
        expected = ['index.html','archive/index.html',f'post/{self.post.pk}/index.html','404.html','CNAME','.nojekyll','robots.txt','sitemap.xml','archive-manifest.json','static/core/archive.css']
        for relative in expected:
            self.assertTrue((self.output_dir / relative).exists(), relative)
        home = (self.output_dir / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Frozen in amber.', home)
        manifest = json.loads((self.output_dir / 'archive-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['record']['public_posts'], 1)
        self.assertEqual(manifest['record']['comments'], 1)
        self.assertEqual(manifest['record']['likes'], 1)
        self.assertTrue(manifest['integrity']['archive_fingerprint'])
