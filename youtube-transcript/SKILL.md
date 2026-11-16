---
name: youtube-transcript
description: Fetch, clean, and archive the transcript of a YouTube video as a news-wiki source document, then continue the standard ingest workflow. Retrieves video metadata and captions with yt-dlp (manual subtitles preferred over auto-captions), deduplicates rolling auto-caption windows with the bundled cleaner, archives to archive/YYYY/MM/DD with a provenance header, and flags ASR artifacts. Use when the user says "ingest this YouTube video/URL", "get the transcript of", "fetch the captions of", or supplies a youtube.com/watch or youtu.be URL together with an ingest request. Covers the video branch of AGENTS.md §"Ingest workflow".
---

# YouTube transcript ingest

This skill extends the URL branch of `AGENTS.md` §"Ingest workflow" to video
sources.  The deliverable is a cleaned transcript archived under
`archive/YYYY/MM/DD/` plus the metadata needed by the rest of the ingest
workflow (summary page, typed pages, unknowns, log entry).

## When to use

Trigger phrases: **"ingest this YouTube video"**, a bare `youtube.com/watch`
or `youtu.be` URL in an ingest request, **"get/fetch the transcript of"**,
**"pull the captions of"**.

Do **NOT** fire for:

- Non-video URLs (plain webfetch branch of the ingest workflow).
- Videos the user only wants summarized in chat without archiving.

## Preconditions

Tools (install once, with the host's pip):

```
pip install --user --break-system-packages yt-dlp curl_cffi
export PATH="$HOME/.local/bin:$PATH"
```

* `yt-dlp` — the maintained successor of `youtube-dl`; **never install
  `youtube-dl`** (abandoned).
* `curl_cffi` — lets yt-dlp impersonate a browser; without it YouTube
  bot-blocking is more likely.
* `youtube-transcript-api` is **IP-blocked on this host** — do not use it.

Keep yt-dlp current (`pip install --user --break-system-packages -U yt-dlp`);
YouTube breaks old extractors regularly.

## Procedure

### Step 1 — metadata

```
yt-dlp --skip-download --dump-json URL
```

Keep: `id`, `title`, `channel`/`uploader`, `upload_date`, `duration`,
`live_status`.  The **upload date** determines the `archive/YYYY/MM/DD/` path
(exceptions: a premiere/live video published later than recorded — use the
publish date and note the recording date in the header).

### Step 2 — captions

Try manual subtitles first (real punctuation, no rolling duplication), then
auto-captions:

```
yt-dlp --skip-download --write-subs --write-auto-subs \
       --sub-langs "ro.*,ro,en" --sub-format "vtt/srt" -o "yt-%(id)s" URL
```

Set `--sub-langs` to the wiki's languages (the example shows Romanian).
Prefer, in order: a manual subtitle track in the video's language → the
`<lang>-orig` auto track → any auto track.  `.srt` output (manual tracks)
needs no cleaning; `.vtt` auto tracks do.

If **no captions exist at all**, fall back to local transcription:

```
yt-dlp -x --audio-format mp3 -o "yt-%(id)s.%(ext)s" URL
pip install --user --break-system-packages faster-whisper
```

Transcribe with `faster-whisper` (small/base model is usually enough; accept
several CPU-minutes per 30 min of audio).  This also handles mixed-language
audio (e.g. a Romanian briefing with a Russian statement) better than
single-language auto-captions.

### Step 3 — clean

```
python3 scripts/clean_vtt.py yt-<id>.<lang>-orig.vtt -o yt-<id>.txt
```

(`scripts/clean_vtt.py` relative to this skill's directory.)  The script
strips karaoke tags, merges rolling-caption windows, and converts `>>`
speaker markers to paragraph breaks.  Expect roughly 100–120 words/minute of
speech; a wildly different count means the merge went wrong — re-run and
inspect.

### Step 4 — quality pass (read before archiving)

Auto-captions contain ASR errors.  While reading the transcript:

* Proper names and numbers are the usual victims (e.g. "Stoian Auglu" =
  Stoianoglo, "133/216" = 133/2016, dropped digits in sums).
* **Never silently correct** — the transcript is the record.  Note suspected
  artifacts in the archive header and record genuine unknowns (unclear
  references, uncertain amounts) in `wiki/unknowns.md` during the ingest.
* Speakers are not named in captions; do not guess identities from voice.
* Mixed-language statements (e.g. Russian inside a Romanian briefing) may be
  transliterated or garbled — flag them.

### Step 5 — archive

Write `archive/YYYY/MM/DD/<channel-slug>.md`:

```markdown
---
title: "<video title> (<channel>, YouTube transcript)"
source: https://www.youtube.com/watch?v=<id>
channel: <channel>
published: YYYY-MM-DD
duration: MM min (SSSS s)
language: <main language> (with <other> passages)
provenance: <manual subtitles | auto-generated captions cleaned with scripts/clean_vtt.py | faster-whisper local transcription>
---

# <video title> (transcript)

<one-paragraph context: what the video is, which wiki pages link to it>

NOTE: transcription artifacts (examples).

---

<cleaned transcript>
```

### Step 6 — continue the standard ingest workflow

Resume `AGENTS.md` §"Ingest workflow" from step 2 (read the full source,
discuss takeaways with the user, then summaries/typed pages/unknowns/log).

## Failure handling

* **HTTP 429 / "Sign in to confirm you're not a bot"**: wait a few minutes and
  retry once with `--extractor-args "youtube:player_client=web_safari"`; if it
  still fails, report to the user and offer to ingest a transcript they
  supply manually.
* **Impersonation warning**: means `curl_cffi` is missing — install it.
* **`RequestBlocked` from youtube-transcript-api**: expected on this host; do
  not retry, use yt-dlp.

## Guardrails

* The archived transcript is immutable once written (same rule as `raw/`).
* Corrections of fact go in wiki pages, citing the transcript; the transcript
  file itself is never edited after archiving.
* Always record in `wiki/log/` that the source is a caption transcript and
  which pipeline produced it (provenance field).

## Reference

* Section this skill extends: `AGENTS.md` → "Ingest workflow" step 1.
* Bundled script: `scripts/clean_vtt.py` (validated in the romania-news
  wiki on the 29 September 2026 Parliament briefing video, id
  `Hluk5ZIukdA`).
* Precedent ingest (romania-news wiki):
  `archive/2026/09/29/parlament-briefing-suspendare-sandu-transcript.md`
  and its log entry `wiki/log/20260929T162000+0300.md`.
