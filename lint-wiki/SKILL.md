---
name: lint-wiki
description: Run the news-wiki lint checklist and produce a numbered findings report with suggested fixes. Checks for contradictions between pages, orphan pages, missing concept pages for mentioned entities, outdated claims, page-format conformance, link-format conformance (standard markdown with leading slash, no wikilinks), type-vs-directory consistency, and index.md coverage of every generated page. Use when the user says "lint the wiki", "audit the wiki", "run the wiki lint", or "check the wiki for lint". Implements AGENTS.md §"Lint" as a bounded, delegatable procedure that returns a report rather than performing edits.
---

# Lint the news wiki

This skill runs the wiki-wide audit defined in `AGENTS.md` §"Lint" and
returns a numbered findings report.  It **does not edit** the wiki — the
report is the deliverable.  Fixes land in follow-up work, at the user's
direction.

## When to use

Trigger phrases: **"lint the wiki"**, "audit the wiki", "run the wiki
lint", "check the wiki for lint", "wiki lint report".

Also fire proactively when the user has just completed a large ingest
or restructuring and asks for a health check before the next piece of
work.

Do **NOT** fire for:

- Linting individual pages (that is a Read + inspection task, not this
  skill).
- Style-only concerns (heading capitalisation, wording).  The lint
  checklist is structural.

## What the lint checks (per AGENTS.md §"Lint")

Each check corresponds to a numbered finding class in the report.

1. **Contradictions between pages.**  Two generated pages saying
   incompatible things about the same subject.  Cite both pages and
   the sentences that contradict.
2. **Orphan pages.**  Any file under `wiki/summaries`, `wiki/concepts`,
   `wiki/organizations`, `wiki/places`, `wiki/events`,
   `wiki/timelines`, `wiki/cases`, `wiki/answers` that receives no
   inbound links from any other wiki page.  Exclude `index.md`
   (structural, expected to be an entry point).
3. **Entities mentioned without a page.**  Named entities or ideas
   appearing repeatedly in generated pages that do not have their own
   page in the appropriate typed directory (`wiki/concepts`,
   `wiki/organizations`, `wiki/places`, `wiki/events`,
   `wiki/timelines`, `wiki/cases`, `wiki/people`).  Report the entity
   name and 2-3 pages that mention it.
4. **Potentially outdated claims.**  Claims contradicted by a newer
   source ingested since the page was written (check `last-updated`
   against newer sources on the same subject).
5. **Page-format conformance.**  Pages missing required frontmatter
   fields (`title`, `Summary`, `Sources`, `type`, `date-created`,
   `last-updated`), frontmatter that is not valid YAML, or a wrong
   `type:` value.  Per `AGENTS.md` §"YAML correctness rules", report
   separately:
   - **Strict-YAML failure**: the frontmatter does not parse with a
     strict YAML parser (verify with e.g.
     `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]).read().split('---')[1])" file.md`).
     The most common cause is an unquoted colon-and-space inside an
     unquoted `title:` or `Summary:` value.
   - **Quoting-convention violation**: `title:` or `Summary:` is not
     a single-line double-quoted string (internal `"` must be
     escaped as `\"`, `\` as `\\`; multi-line values are not
     permitted).
   Sub-check by directory (each is a distinct defect class — report
   separately when a page fails more than one):
   - `type:` must match the directory's document class: `summary`
     (`wiki/summaries/`), `concept` (`wiki/concepts/`),
     `organization` (`wiki/organizations/`), `place`
     (`wiki/places/`), `event` (`wiki/events/`), `timeline`
     (`wiki/timelines/`), `case` (`wiki/cases/`), `answer`
     (`wiki/answers/`), `person` (`wiki/people/`), `log`
     (`wiki/log/`), per `AGENTS.md` §"Page format" and
     §"Structured frontmatter for typed pages".
6. **Link-format conformance.**  Per `AGENTS.md` §"Link format",
   internal wiki links MUST use standard Markdown links with a
   **leading `/`** (root-relative).  Report any link that:
   - Uses Obsidian wikilink syntax (`[[…]]`).
   - Omits the leading `/` for an internal wiki link.
   - Is broken (target file does not exist at the root-relative path).
7. **index.md coverage.**  For each of `wiki/summaries/`,
   `wiki/concepts/`, `wiki/organizations/`, `wiki/places/`,
   `wiki/events/`, `wiki/timelines/`, `wiki/cases/`, `wiki/answers/`,
   `wiki/people/`, verify that the directory's `index.md` links to
   every `.md` file in the directory (excluding `index.md` itself).
8. **`wiki/log/index.md` coverage.**  Verify that every file in
   `wiki/log/` (excluding `index.md` itself) has a bullet in
   `wiki/log/index.md`, newest first, and that each bullet's date and
   one-line description match the entry's frontmatter `title:` and
   filename timestamp (per AGENTS.md §"Lint").
9. **Disclaimer and backlink placement.**  Check that
   `wiki/summaries`, `wiki/answers`, and `wiki/concepts` pages carry
   the legal disclaimer at the bottom of the page, that the backlinks
   list immediately follows `## Backlinks` (or reads "No backlinks
   (yet)"), and that the disclaimer is the very last thing on the
   page.

## Procedure

### Step 1 — plan the sweep

Announce to the user which checks you will run.  If the wiki is very
large, offer to run the sweep in phases (e.g. checks 1-4 first, 5-8
second) — checks 3 and 4 in particular can be time-expensive.

### Step 2 — delegate to a read-only subagent

The lint sweep is a bounded read-only inspection with a large search
scope.  Delegate to a fresh-context read-only subagent — in Hermes via
`delegate_task`, in OpenCode the `explore` subagent — with a
**precise, exhaustive prompt** naming:

- Every check from the list above.
- The specific paths to sweep for each check.
- The format for the returned report (see Step 3).

Instruct the subagent to **not attempt fixes** — its output is a
findings list only.

This delegation keeps the multi-file scan out of the main context;
only the final report returns.

### Step 3 — assemble the findings report

The subagent's output should be a single markdown document with this
shape (present it to the user verbatim):

```markdown
# News-wiki lint report — YYYY-MM-DD HH:MM

Summary: N findings across M check categories.

## 1. Contradictions (K findings)

1. **[<page-A>](wiki/…) vs [<page-B>](wiki/…)** — [page-A] says "…"
   while [page-B] says "…" on the same subject (<what subject>).
   Suggested fix: <which page to update, or "flag as contradiction
   requiring owner ruling">.

## 2. Orphan pages (K findings)

1. **[<page>](wiki/…)** — no inbound links from any wiki page.
   Suggested fix: <either add inbound links from N related pages,
   or delete if the page is no longer relevant>.

## 3. Entities mentioned without a page (K findings)

1. **<entity name>** — mentioned in [page-A], [page-B], [page-C]
   with no dedicated page.  Suggested fix: <create the page in the
   appropriate typed directory, or clarify why not>.

## 4. Potentially outdated claims (K findings)

## 5. Page-format defects (K findings)

## 6. Link-format defects (K findings)

## 7. index.md coverage gaps (K findings)

## 8. Disclaimer / backlink placement defects (K findings)

## Summary of suggested actions

- Immediate (blocks other work): <list>
- Should schedule: <list>
- Cosmetic / can defer: <list>
```

### Step 4 — offer follow-up

After presenting the report, offer the user the option to have
specific findings fixed: the user picks numbers; you apply the
suggested fixes (each fix session ends with a `write-log-entry`
invocation).

Do NOT auto-apply fixes without confirmation.  Lint findings often
require a judgement call about which page to change; the user is the
right person to make that call.

### Step 5 — log the lint pass

Whether or not fixes were applied, if the lint pass itself produced
substantive findings, invoke `write-log-entry` to record the pass.
The log entry names the check counts and the disposition (findings
fixed inline, findings deferred).  If the lint pass was clean
(0 findings), a log entry is optional but useful as a health signal.

## Guardrails

- **The lint report is read-only work.**  No edits to the wiki are
  made during the sweep.  Edits happen only in follow-up, at the
  user's direction.
- **Do not over-report.**  A page with three format defects gets one
  numbered finding, not three — group related defects on the same
  page.  Signal-to-noise matters when the report gets long.
- **Cite pages by path.**  Use wiki-repo-relative paths (`wiki/…`) so
  the report is greppable from the repo root.

## Reference

- Section this skill implements: `AGENTS.md` → "Lint".
- Related skills invoked in follow-up: `write-log-entry` — to record
  the pass.
- Delegation target: a fresh-context read-only subagent (Hermes:
  `delegate_task`; OpenCode: `explore`) — it runs the multi-file sweep so
  the main context sees only the report.
