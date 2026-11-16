---
name: write-log-entry
description: Create a wiki/log/YYYYMMDDTHHMMSS+hhmm.md entry recording a change to the wiki, and prepend the one-line summary bullet to wiki/log/index.md. Use whenever any files under wiki/ have been created or modified (per AGENTS.md §"The wiki/log/ directory"), including after ingest/update runs, restructuring, or answering a question that produced a saved answer page. Trigger phrases include "write a log entry", "log this change", "add a log", "record this in wiki/log", and any workflow instruction that ends with "add a wiki/log entry".
---

# Write a wiki/log entry

Every change to the wiki gets one `wiki/log/` entry.  This skill produces
that entry and updates `wiki/log/index.md`.  It replaces the procedural detail
of `AGENTS.md` §"The wiki/log/ directory".

## When to use

Invoke this skill whenever:

- Files under `wiki/` were created or modified in the current session — every
  workflow (ingest, update, restructuring, answers saved) ends here.
- The user explicitly says "write a log entry", "log this", "add to the log",
  or points at `wiki/log/`.

Do **not** invoke this skill for:

- Changes limited to files outside `wiki/` (e.g. `.opencode/`, root-level
  configs, files in `raw/` — although edits to `raw/` almost always
  accompany wiki-page edits, in which case log the wiki-page edits).
- Speculation or partial thoughts the user did not act on.  The log is for
  what changed, not what was considered.

## Preconditions

Before writing the log entry, confirm you know:

1. **The list of files changed** — the log
   entry's `Sources:` frontmatter list and `## Changed files` body list
   must both be exhaustive for this change.
2. **The rationale** — one or two sentences: *why* the change was made,
   not merely *what*.  Cite the driving instruction (user request or
   quoted instruction).
3. **The current local timezone offset** — use `date +%z` or
   `date -Iseconds` to get the host's current offset (DST-aware).  ISO-8601 basic format requires the offset without a colon in
   the filename (`+0300`, not `+03:00`).

## Procedure

### Step 1 — pick the filename

Format: `wiki/log/YYYYMMDDTHHMMSS+hhmm.md`  (ISO-8601 basic; Windows-safe:
no colons).  Example: `wiki/log/20260907T143000+0300.md`.

Use the current local time.  Run `date +%Y%m%dT%H%M%S%z` to construct the
stem; verify the resulting filename does not already exist (collisions on
the same second are rare but possible if multiple entries land in one
session — bump to the next second in that case).

### Step 2 — write the entry

Use this exact structure (this replaces the section in `AGENTS.md`
verbatim):

```markdown
---
title: "YYYY-MM-DD HH:MM — one-line description of the change"
type: log
Sources:
  # Exhaustive list of files changed by this action.
  # Use wiki-repo-relative paths (no leading slash).
  - wiki/path/to/file1.md
  - wiki/path/to/file2.md
date-created: YYYY-MM-DDTHH:MM:SS+03:00
---

# YYYY-MM-DD HH:MM — one-line description of the change

## What happened

One or two sentences of *what the user asked for* (verbatim quote if
succinct) and *what was done in response*.  This is the paragraph
future-you will grep for.

## Rationale

Why this change.  Cite the driving instruction (user quote).  If the
change resolves a contradiction, name the contradiction.  If it
applied a workflow, name the `AGENTS.md` section or skill that
governed it.

## Changed files

- `wiki/path/to/file1.md` — one-line summary of the change to this file.
- `wiki/path/to/file2.md` — one-line summary of the change to this file.

## Related

- Cross-links to the answer / summary / typed pages this entry is
  evidence for.  Optional.
```

Rules for the body:

- **Quote the `title:` value.**  Log titles almost always contain a
  colon-and-space (the HH:MM timestamp, description colons), which
  silently breaks strict YAML when unquoted.  Per `AGENTS.md` §"YAML
  correctness rules", `title:` and any `Summary:` MUST be single-line
  double-quoted strings; the quotes are YAML syntax, and the value
  they encode is what must match the H1 verbatim.
- **Filename `date-created` MUST match the timestamp in the filename** —
  same Y/M/D/H/M/S and offset.  A mismatch is a lint defect.
- **`title:` and the H1 heading MUST match** verbatim.  The one-line
  description is what appears in `wiki/log/index.md` and in the
  frontmatter of related pages that list this log.  Choose it
  deliberately.
- **`Sources:` must be exhaustive** for this change.  If the user later
  greps the log for "which entry touched file X?", the answer must be
  findable via `Sources:` lists.
- **Cite AGENTS.md sections by name** when the entry describes applying
  a workflow (e.g. "…per AGENTS.md §'Ingest workflow'…").  This is how
  future readers verify the workflow was followed.
- Content-length norm: 5–30 lines of prose is typical.  Substantive
  investigations and multi-file restructurings run longer; trivial
  one-file edits run shorter.  There is no maximum, but there is a
  floor: an entry that says only "updated files" is not enough —
  future you cannot use it.

### Step 3 — update `wiki/log/index.md`

Prepend a single bullet to the top of the list (newest first — the file
is reverse chronological).  Format:

```markdown
* **YYYY-MM-DD HH:MM** [one-line description of the change](./YYYYMMDDTHHMMSS+0300.md): One-sentence to one-paragraph summary of what the entry says.  This is the text a reader scans before deciding to open the entry itself.
```

Keep the bullet self-contained (do not require the reader to open the
entry to know what happened), but shorter than the entry itself — one
paragraph is the norm; two if the change had multiple substantive
threads.  Match the tone of the entries already in `wiki/log/index.md`.

### Step 4 — verify

- The new file exists at the expected path.
- `date-created`, filename timestamp, `title:`, H1, and the bullet in
  `wiki/log/index.md` all agree on the timestamp and one-line
  description.
- The `Sources:` list matches the files actually touched.

### Step 5 — search-index refresh (wiki-dependent)

In the reference wiki (romania-news) none is needed: its search-index
layers — **QMD** and a **lemonade-backed semantic sidecar**
(`tools/vecsearch.py` + `.vectors/`) — were removed on 14 October 2026 as
unreliable on the host (embedding-session expiries under memory pressure;
the lemonade endpoint returning HTTP 500), and discovery now runs on the
wiki's own indexes plus `grep`/ripgrep.  In a wiki that maintains a
search index, refresh it here per that wiki's `AGENTS.md`.  Otherwise
the workflow ends at Step 4 (verification).

## Guardrails

- **Never modify a prior log entry.**  The log is append-only.  If you
  discover a factual error in a prior entry, write a *new* entry that
  cites the prior one and states the correction — do not rewrite
  history.
- **Never delete a log entry.**  If a change is reversed, write a new
  entry describing the reversal; keep the original entry as history.
- **Do not batch multiple unrelated changes into a single entry.**  One
  log entry per coherent unit of work is the norm.  If you did two
  independent things in one session, write two entries.  Fine to merge
  tightly-related edits (e.g. a page + index.md + reciprocal
  cross-links) into one entry because they are one unit of work.
- **Local timezone offset** — use the host's current local offset
  (`date +%z`, DST-aware).  Do not use `Z` / UTC.

## Reference

- Section this skill replaces: `AGENTS.md` → "The wiki/log/ directory"
- Related skills that end by invoking this one: `lint-wiki` (after
  fixes are applied at the user's direction).
- Recent examples worth reading before writing your first entry:
  the newest files in `wiki/log/`.
