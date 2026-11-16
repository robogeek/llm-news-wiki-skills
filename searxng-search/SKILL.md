---
name: searxng-search
description: "Search the web via SearXNG (JSON API, two instances) across categories - news, general, videos, it, science, social media - with country scoping (RO, GR, ...) and per-domain site: filters, then vet the hits for the wiki ingest workflow. Use when the user says \"perform a news search in countries RO, GR for TOPIC\", \"news search in countries RO, GR for TOPIC\", \"general/videos/it/science/social media search for X\", \"search the web for X in RO\", or asks to find articles to fill a wiki gap/unknown. Returns vetted candidate articles, not archived ingests."
---

# SearXNG search (news / general / videos / it / science / social media)

Searches the SearXNG instances (with OpenSerp as an independent backup) for
the user's topic, scoped by category and country, normalizes the results,
and (when the goal is wiki ingestion) vets the best hits and presents
candidates for approval before any ingest.

## Command grammar

Both phrasings mean the same thing:

```
perform a <CATEGORY> search in countries <CC>[, <CC>...] for <TOPIC QUERY PHRASE>
<NEWS|GENERAL|VIDEOS|IT|SCIENCE|SOCIAL MEDIA> search in countries <CC>[, <CC>...] for <TOPIC>
```

It means there are three slots in this query pattern:

1. The `<CATEGORY>` which designates the type of search to perform
  - This maps to the search category selector in the SearxNG user interface, and in the configuration
  - `<CATEGORY>` maps to the SearXNG category: **news**, **general**, **videos**, **it**, **science**, **social media**.
  - No category given maps to a **general** web search
1. The country or countries in which to perform the search
  - This maps to the country selector in the SearxNG user interface
  - Countries are ISO alpha-2 codes (`RO`, `GR`, `MD`, `HU`, ...). SearXNG has
    no country parameter — each country maps to its primary **language**
    (`RO→ro`, `GR→el`, `MD→ro`, ...; full table in the script), and the skill
    runs **one query per language**, merging and deduping by URL. Translate the
    topic into each target language when the user did not (e.g. Romanian
    "moțiunea de cenzură", Greek "ψήφο δυσπιστίας") — run both the user's
    phrasing and the translation when unsure.
  - No countries given → a single unlocalized query.
1. The topic query phrase, which is the discussion of the search intent

The topic query phrase might be expressed as a question to answer, or as a claim to validate.  The user may write several sentences, which may contain several questions, and/or several claims to validate.  The user may also present one or more theories, which should be taken as one or more claims to validate.

## Generating a list of search queries

1. Convert the _topic query phrase_ into one or more _search engine query_ phrases.
  - Most likely the user's query phrase will be one or more questions to answer, and/or one or more claims which must be validated
  - The provided text must be analyzed to generate a list of queries that are useful as search engine queries
2. Translate each _search engine query phrase_ into primary the language spoken by each country specified by the user
  - While the user writes the query phrase in their language, it is more useful to make the query in the primary language of the target country

That results in a list of searches to perform where each are:

1. The category
2. One of the countries
3. One of the search engine queries, translated to the primary language of the country

## Instances

| role | Type | URL | status (verified 2026-11-16) |
|---|---|---|---|
| **primary** (`--base-url` default) | SearxNG | `https://searxng-ai-nuc3.tailbedcb3.ts.net` | UP, JSON API enabled |
| **second** (`--alt-base-url` default) | SearxNG | `https://searxng-ai.tailbedcb3.ts.net` | UP, JSON API enabled |
| **OpenSerp** (`--openserp-base` default) | OpenSerp | `https://openserp.tailbedcb3.ts.net` | UP; `/health` lists google/yandex/baidu/bing/duckduckgo/ecosia |

- **Search strategy**: run the query on the primary; on failure or zero
  results the script automatically falls through the chain below (second
  instance → engine-routed retry → OpenSerp). Pass `--openserp-always` to
  merge OpenSerp results in addition when coverage matters more than latency.
- The former LAN address `http://192.168.8.15:3080` no longer responds from
  this host — do not use it.
- **JSON 403 diagnosis**: SearXNG answers `/search?...&format=json` with 403
  when the instance's `formats:` setting lacks `json` (HTML still works).
  Both instances have JSON enabled as of 2026-11-16. If a 403 reappears
  after instance maintenance, the fix needs the instance admin to add
  `json` to `formats` in `settings.yml` — which is read at startup, so
  restart the container afterwards and confirm the edit landed in the
  settings file the container actually mounts (this bit once: the edit
  went into the wrong config). Do not retry blindly; use the other
  instance or report.
- OpenSerp API shape: `GET /{engine}/search?text=<query>&lang=ro&limit=10`
  → a JSON **list** of `{title, url, snippet, domain, ...}`.

## Fallback chain

Each stage runs only when everything before it produced **zero results**
(disable with `--no-fallback`); the exception is `--openserp-always`, which
merges OpenSerp in regardless:

1. **Primary instance** — the normal query (`--base-url`).
2. **Second instance** — the same query on `--alt-base-url` (catches a down
   or degraded primary).
3. **Engine-routed retry** on each instance — same query with
   `engines=bing,yahoo,yandex,seznam,yep,qwant` (`--fallback-engines` to
   change). **Why**: the big four (brave, duckduckgo, google, startpage)
   accumulate *runtime* suspensions ("too many requests", CAPTCHA, access
   denied) that **do not clear on instance restart** — verified 29 October
   2026, when an updated+restarted instance still had all four suspended.
   The smaller engines keep working. Diagnose via the `/search` response's
   `unresponsive_engines` field or `/healthz`.
4. **OpenSerp** (`--openserp-base`, `--openserp-engines`, `--openserp-limit`)
   — queries google/bing/duckduckgo/yandex/ecosia on the independent
   instance. **Caveats**: a different index view (expect name collisions);
   no country scoping (pass `lang`); results carry no dates (verify on the
   article page).

Every fallback is reported in the output header (`# fallbacks used: ...`)
and in the `--json` payload (`"fallbacks"`). Tune or disable per query.

## Running queries

Use the bundled script (relative to this skill's directory):

```
python3 scripts/searxng_search.py <terms...> [-c news|general|videos|it|science|social media] \
    [-l RO] [-l GR] [--site digi24.ro] [--pages N] [--time-range week] \
    [--exact] [--engines bing,qwant] [--json] [--base-url URL] [--alt-base-url URL] \
    [--no-fallback] [--fallback-engines bing,yahoo,yandex,seznam,yep,qwant] \
    [--openserp-base URL] [--openserp-engines google,bing,duckduckgo,yandex,ecosia] \
    [--openserp-always]
```

Examples (from the 30 September 2026 gap sweep):

```
python3 scripts/searxng_search.py "moțiunea de cenzură" Bolojan PSD AUR -c news -l RO
python3 scripts/searxng_search.py motiune cenzura Bolojan -l RO --site senat.ro --pages 2
python3 scripts/searxng_search.py "textul integral" motiune cenzura -l RO
```

## Field tactics (learned the hard way)

- **Flaky engines are normal.** `google`, `startpage`, `brave`, `duckduckgo`
  intermittently return CAPTCHA/rate-limit errors; the script reports them
  under `# unresponsive engines`. Retry once after a few seconds; if a
  category comes back empty, try again with `--engines bing,qwant,yahoo`.
  **Runtime suspensions survive instance restarts** — if the big four are
  suspended, let the fallback chain handle it (or route manually with
  `--engines bing,yahoo,yandex,seznam,yep,qwant`).
- **Ambiguous words need scoping.** Romanian "AUR" = the metal *and* the
  party; quotes (`--exact`) plus `--site <outlet>` fix it. Bing honors
  `site:`, including `site:senat.ro` for primary documents.
- **`publishedDate` is often empty** and engines' `time_range` is coarse
  (day/week/month/year). For a historical window (e.g. "late April 2026"),
  search without a filter and verify dates on the article page itself before
  treating them as fact.
- **404 on fetch** (stale or mangled URL): re-search the exact article title
  to find the live URL — `.html` vs `.htm` suffixes differ between indexes.
- **PDFs**: check for a text layer (`pdftotext file.pdf - | wc -c`) before
  planning to ingest; senat.ro motion scans are image-only. If no OCR is
  available, look for a full-text republication by an outlet instead.
- **Paginate before concluding absence**: 2 pages (`--pages 2`) on two
  phrasings beats one query.

Per-country outlet lists for `--site` scoping are **per-wiki** content:
maintain them in that wiki's own docs (e.g. its `WEB-SEARCH.md`), not in
this shared skill.

## From hits to wiki ingest

This skill **searches and vets; it does not archive.** When the search feeds
an ingest:

1. **Rank** hits against the purpose — for a gap sweep, the gaps are listed
   in `wiki/unknowns.md`; prefer primary/official documents (parliament,
   ministry, court sites) and full-text republications over short relays.
2. **Dedupe** against `archive/` (the article may already be ingested).
3. **Vet** the top candidates with the `webfetch` tool (or `curl` for PDFs);
   confirm the date and the content actually covers the target.
4. **Present the shortlist with takeaways to the user and get approval**
   before running the ingest workflow (per `AGENTS.md` §"Ingest workflow",
   step 3 - discuss key takeaways before writing anything).
5. After ingest, update the resolved entries in `wiki/unknowns.md` per its
   maintenance rules, and write the `wiki/log/` entry.

## Reporting

Always report: the query/category/languages actually run, the result count,
the unresponsive engines, and the vetted shortlist (date | title | URL | why
it matters). If nothing usable surfaced, say so and list the phrasings tried.
