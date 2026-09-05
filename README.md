# Krine

Krine is a thought experiment about what an anonymous social platform could look like. The live application is being retired into **Krine / Closed Network**, a read-only static archive at `krine.ca`.

## Archive state

Krine now supports a sealed archive mode. With `ARCHIVE_MODE=True`, write methods fail closed, the Django admin is not mounted, analytics are disabled, and the interface becomes a read-only record. Only posts matching `is_analyzed=True AND is_flagged=False` appear in the public archive.

The archive keeps the original visual language, but treats the site as a closed network rather than a broken app: final public-entry counts, recorded activity dates, immutable entry pages, comments, like totals, timestamps, tags, and surviving media are preserved.

## Static export

Generate the GitHub Pages version from the production database with:

```bash
python manage.py export_archive \
  --domain krine.ca \
  --closed-date YYYY-MM-DD
```

The exporter writes to `docs/` by default and creates:

- the final public feed
- one static page per surviving public post
- preserved public comments, tags, like totals, timestamps, and referenced media
- the About / Mission / FAQ / Legal / Security / Safety pages
- an Archive Record page
- `CNAME`, `.nojekyll`, `robots.txt`, and `sitemap.xml`
- `archive-manifest.json` with SHA-256 hashes and an archive fingerprint

If a public post references media that cannot be copied, export stops rather than silently producing an incomplete archive. `--allow-missing-media` exists only for intentional loss.

## Before retiring the server

Do **not** destroy the DigitalOcean Droplet just because the static export succeeds. First preserve private backups of the production PostgreSQL database and production media.

Recommended retirement sequence:

1. back up production PostgreSQL
2. back up the production media directory
3. run the static export
4. inspect `docs/` and `archive-manifest.json`
5. publish `docs/` with GitHub Pages at `krine.ca`
6. verify DNS, HTTPS, posts, comments, images, search/filter/sort, and the Archive Record page
7. only then destroy the old server

## Original features

- **Anonymous Posting** — no account registration.
- **AI Moderation** — posts were analyzed for safety and tagged with emotional/topical labels.
- **Community Interaction** — session-based likes and anonymous comments.
- **Smart Discovery** — sort by Newest, Popular, or Most Commented; filter by post type.

## Tech stack

- **Backend:** Django 5+
- **Frontend:** HTML, vanilla CSS, vanilla JavaScript
- **AI/ML:** PyTorch + Hugging Face Transformers
- **Database:** SQLite by default; PostgreSQL supported via `DATABASE_URL`
- **Cache:** optional Redis
- **Object storage:** optional S3-compatible storage
- **Archive target:** static HTML/CSS/JS on GitHub Pages

## Development

Run tests before merging archive changes:

```bash
python manage.py test core
```

## License

Krine is released under the [MIT License](LICENSE).

Made with love by sj.
