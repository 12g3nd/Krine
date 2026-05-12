# Krine

Krine is a thought experiment about what an anonymous social platform could look like. It aims to empower users to share thoughts freely while leveraging local AI for content safety and organization.

## AI Note

The project was created using a lot of help from Google's Antigravity and Claude Code.

## Features

- **Anonymous Posting** — no account registration, ever.
- **AI Moderation** — every post is analyzed for safety (filtering harmful content) and tagged with emotional/topical labels.
- **Community Interaction** — session-based likes and anonymous comments.
- **Smart Discovery** — sort by Newest, Popular, or Most Commented; filter by post type or time window.

## Tech Stack

- **Backend**: Django 5+
- **Frontend**: HTML, vanilla CSS, vanilla JavaScript
- **AI/ML**: PyTorch + HuggingFace Transformers (zero-shot classification)
- **Database**: SQLite by default; PostgreSQL supported via `DATABASE_URL`
- **Cache (optional)**: Redis
- **Object storage (optional)**: any S3-compatible service


## AI moderation

Every new post is analyzed in a background thread before it becomes visible
in the public feed. The pipeline is two stages:

1. **Regex pre-check** — emails and phone numbers are flagged immediately.
2. **Zero-shot classification** against two label sets:
   - **Safety**: Safe, Hate Speech, Violence, Harassment, Personal Information
   - **Vibes** (top 3 are stored as tags): Nostalgic, Hopeful, Melancholy,
     Venting, Confession, Lonely, Healing, etc.

Posts trip the safety filter when:

- the `Safe` score collapses below 3%, or
- `Harassment` exceeds `Safe` by 3× and is itself above 0.10 (catches
  targeted attacks while letting general venting through), or
- `Violence`, `Hate Speech`, or `Personal Information` cross fixed
  thresholds.

## Contributing

Pull requests are welcome. To keep things sane:

- Run `python manage.py test core` before opening a PR.
- For UI changes, please test the create/list/detail flows in a browser.
- Don't commit `.env`, the SQLite database, or the HuggingFace model cache.
- Keep new dependencies minimal and justify them in the PR description.

## License

Krine is released under the [MIT License](LICENSE).

Made with love by sj
