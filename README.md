# Krine

Krine was a small anonymous social experiment. It is now permanently retired as **Krine / Closed Network**, a read-only static archive at `https://krine.ca`.

No application server, database, moderation worker, account system, or writable endpoint remains online. The public site is served entirely from `main:/docs` with GitHub Pages.

## Final public record

- **Opened:** 2026-01-26
- **Last public entry:** 2026-06-03
- **Sealed:** 2026-09-05
- **Public entries:** 83
- **Comments:** 14
- **Recorded likes:** 10,683
- **Public media files:** 0
- **Record ID:** `KRN-20260126-20260905-0083`
- **Sealed capture fingerprint:** `f6b70f0b9548cbcf3941dfa2222c2ded7f92141f88552a96f4b6268fbc9d2d6f`

The static artifact includes a machine-readable `docs/archive-manifest.json` with per-file SHA-256 hashes and the current artifact fingerprint. The original seal fingerprint is retained separately so the first production-derived capture remains identifiable even after small archival epilogue improvements.

## Closed Network

The archive preserves only public posts that had completed moderation and were not flagged:

```text
is_analyzed=True AND is_flagged=False
```

It preserves public post text, tags, comments, like totals, timestamps, and any media referenced by surviving public posts. Browser sessions, reports, moderation-only records, server logs, environment variables, credentials, model files, and the production database are deliberately absent from the public artifact.

Search, sorting, and type filtering now run entirely in the browser. Nothing on `krine.ca` writes anywhere.

## Preservation

Before the live DigitalOcean deployment was destroyed, the production PostgreSQL dump, media directory, deployment configuration, and live git commit were preserved privately and hash-verified off-server. Those private materials are intentionally not committed here.

The public archive was validated before retirement:

- Django system check passed
- archive tests: 5/5 passed
- full core tests: 16/16 passed
- 83/83 public entry pages present
- secret/private-data scan clean
- unrendered-template/error scan clean
- live write-control scan clean
- internal-link scan clean
- no missing public media

## Epilogue

The final archive received three deliberately small post-retirement changes:

1. Google Fonts was removed so the archive no longer depends on an external font service.
2. The Archive Record page exposes a shortened form of the original sealed capture fingerprint.
3. A static network-telemetry relic visualizes the preserved monthly entry trace and final silence using only archived data.

These changes do not alter the preserved posts, comments, tags, timestamps, or interaction counts.

## Original application

Krine was built with Django, vanilla HTML/CSS/JavaScript, PostgreSQL, optional Redis, and a Hugging Face zero-shot moderation pipeline. The repository retains the original application and archive-export tooling for historical context.

## License

Krine is released under the [MIT License](LICENSE).

Made with love by sj.
