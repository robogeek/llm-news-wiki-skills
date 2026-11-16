# Shared news-wiki skills

Canonical, wiki-agnostic skills for the news-wiki fleet
(us-politics, romania-news, hybrid-war-russia, …). Wired into each
wiki-serving Hermes profile via `skills.external_dirs`.

## Conventions

- **Source of truth**: the most-developed wiki's `.opencode/skills/`
  (currently **romania-news**). Promote changes INTO this dir; the
  per-wiki `.opencode/skills/` copies are OpenCode-only snapshots and
  drift freely — never treat them as canonical.
- Skills stay wiki-agnostic: no per-wiki names in prose. Per-wiki
  precedents are attributed inline ("validated in the romania-news
  wiki"). Intrinsically-country-specific skills keep their scope
  (`ro-trade-registry` is Romanian by nature).
- Format is the agentskills.io standard (`SKILL.md` with
  `name`/`description` frontmatter + optional `scripts/`), so the same
  dir works for Hermes, OpenCode, and Claude Code.
- Keep `__pycache__/` out of this tree.

## Skills

| skill | purpose |
|---|---|
| `searxng-search` | SearXNG search with country scoping + engine/OpenSerp fallback chain |
| `write-log-entry` | `wiki/log/` entry + `wiki/log/index.md` update |
| `lint-wiki` | wiki-wide audit → numbered findings report (read-only) |
| `ocr-pdf-ingest` | scanned-PDF branch of the ingest workflow |
| `youtube-transcript` | video-transcript branch of the ingest workflow |
| `ro-trade-registry` | Romanian trade-registry lookup (RO-specific) |

## Adding a new wiki profile

1. `hermes -p <profile> config set skills.external_dirs '["/home/david/Projects/wikis/skills"]'`
2. Verify: `hermes -p <profile> skills list` — the six skills show tier `external`.
3. For OpenCode sessions in that wiki, copy (or symlink — untested) these
   dirs into `<wiki>/.opencode/skills/`.
