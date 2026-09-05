import hashlib
import json
import shutil
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone

from core.models import Comment, Post, Reaction

STATIC_PAGES = ('about', 'mission', 'faq', 'legal', 'security', 'safety', 'archive')


class Command(BaseCommand):
    help = 'Render the public Krine record as a static GitHub Pages site.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='docs')
        parser.add_argument('--domain', default='krine.ca')
        parser.add_argument('--opened-date', default='')
        parser.add_argument('--closed-date', default='')
        parser.add_argument('--allow-missing-media', action='store_true')

    def handle(self, *args, **options):
        output = (settings.BASE_DIR / options['output']).resolve()
        root = settings.BASE_DIR.resolve()
        if output == root or root not in output.parents:
            raise CommandError('Output must stay inside the repository root.')

        opened = self._parse_date(options['opened_date'])
        closed = self._parse_date(options['closed_date']) or timezone.localdate()
        domain = self._domain(options['domain'])
        posts = list(Post.objects.filter(is_flagged=False, is_analyzed=True).prefetch_related('tags','comments','reactions').order_by('created_at'))
        opened = opened or (timezone.localtime(posts[0].created_at).date() if posts else closed)
        if opened > closed:
            raise CommandError('Opening date cannot be after closure date.')

        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        self._copy_static(output)
        missing_media = self._copy_media(posts, output, options['allow_missing_media'])

        site_url = f'https://{domain}'
        with override_settings(
            ARCHIVE_MODE=True,
            ARCHIVE_OPENED_DATE=opened.isoformat(),
            ARCHIVE_CLOSED_DATE=closed.isoformat(),
            ARCHIVE_SITE_URL=site_url,
            STATIC_URL='/static/', MEDIA_URL='/media/', GOOGLE_ANALYTICS_ID='',
            ALLOWED_HOSTS=['testserver','localhost','127.0.0.1',domain],
        ):
            client = Client()
            self._render(client, '/', output / 'index.html')
            for page in STATIC_PAGES:
                self._render(client, f'/{page}/', output / page / 'index.html')
            for post in posts:
                self._render(client, f'/post/{post.pk}/', output / 'post' / str(post.pk) / 'index.html')
            request = RequestFactory().get('/404.html', HTTP_HOST=domain)
            (output / '404.html').write_text(render_to_string('core/archive_404.html', request=request), encoding='utf-8')

        self._support_files(output, domain, site_url, posts)
        manifest = self._manifest(output, domain, site_url, opened, closed, posts, missing_media)
        (output / 'archive-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Sealed {len(posts)} public entries into {output}.'))

    def _parse_date(self, raw):
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError('Dates must use YYYY-MM-DD.') from exc

    def _domain(self, raw):
        raw = raw.strip()
        if not raw:
            raise CommandError('Domain cannot be empty.')
        if '://' in raw:
            raw = urlparse(raw).hostname or ''
        if not raw:
            raise CommandError('Invalid domain.')
        return raw

    def _copy_static(self, output):
        source = settings.BASE_DIR / 'core' / 'static' / 'core'
        if not source.exists():
            raise CommandError(f'Missing static source: {source}')
        shutil.copytree(source, output / 'static' / 'core')

    def _copy_media(self, posts, output, allow_missing):
        missing = []
        for post in posts:
            if not post.image:
                continue
            rel = PurePosixPath(post.image.name)
            if rel.is_absolute() or '..' in rel.parts:
                raise CommandError(f'Unsafe media path: {post.image.name}')
            dest = output / 'media' / Path(*rel.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                with post.image.open('rb') as src, dest.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
            except Exception as exc:
                item = f'{post.pk}: {post.image.name}'
                missing.append(item)
                if not allow_missing:
                    raise CommandError(f'Could not copy public media {item}.') from exc
        return missing

    def _render(self, client, path, destination):
        response = client.get(path)
        if response.status_code != 200:
            raise CommandError(f'Render failed for {path}: HTTP {response.status_code}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

    def _support_files(self, output, domain, site_url, posts):
        (output / 'CNAME').write_text(domain + '\n', encoding='utf-8')
        (output / '.nojekyll').write_text('', encoding='utf-8')
        (output / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n', encoding='utf-8')
        urls = [f'{site_url}/'] + [f'{site_url}/{p}/' for p in STATIC_PAGES] + [f'{site_url}/post/{p.pk}/' for p in posts]
        xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        xml += [f'  <url><loc>{escape(url)}</loc></url>' for url in urls]
        xml.append('</urlset>')
        (output / 'sitemap.xml').write_text('\n'.join(xml) + '\n', encoding='utf-8')

    def _manifest(self, output, domain, site_url, opened, closed, posts, missing):
        ids = [p.pk for p in posts]
        comments = Comment.objects.filter(post_id__in=ids).count()
        likes = Reaction.objects.filter(post_id__in=ids, reaction_type=Reaction.LIKE).count()
        files = {}
        for path in sorted(output.rglob('*')):
            if not path.is_file() or path.name == 'archive-manifest.json':
                continue
            rel = path.relative_to(output).as_posix()
            files[rel] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
        fingerprint = hashlib.sha256(''.join(f'{k}:{v["sha256"]}\n' for k,v in sorted(files.items())).encode()).hexdigest()
        return {
            'schema_version': 1,
            'archive': 'Krine / Closed Network',
            'domain': domain,
            'site_url': site_url,
            'generated_at': timezone.now().isoformat(),
            'record': {
                'opened_date': opened.isoformat(), 'closed_date': closed.isoformat(),
                'first_public_entry': posts[0].created_at.isoformat() if posts else None,
                'last_public_entry': posts[-1].created_at.isoformat() if posts else None,
                'public_posts': len(posts), 'comments': comments, 'likes': likes,
                'selection_rule': 'is_analyzed=True and is_flagged=False',
                'missing_public_media': missing,
            },
            'integrity': {'algorithm':'sha256','archive_fingerprint':fingerprint,'file_count':len(files),'files':files},
        }
