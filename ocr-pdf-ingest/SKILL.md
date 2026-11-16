---
name: ocr-pdf-ingest
description: OCR the scanned-PDF branch of a news-wiki ingest workflow - handles image-only PDFs that pdftotext renders empty, by rasterizing pages with pdftoppm and transcribing with tesseract (the wiki language's pack, e.g. `ron` for Romanian; a dpkg -x self-hosting fallback is documented), assembling page-marked text with the bundled pipeline script, then archiving the original PDF + the transcription under archive/ with a provenance header and continuing the standard ingest workflow. Use when the user says "ingest this PDF", "OCR this file/PDF", supplies an archive-style scanned-PDF URL (e.g. cndd.ro, a .gov portal) with an ingest request, or a pdftotext probe of a PDF comes back empty. NOT for ordinary HTML articles (webfetch branch) or YouTube videos (the youtube-transcript skill).
---

# Scanned-PDF OCR ingest

This skill extends `AGENTS.md` §"Ingest workflow" to **scanned PDF** sources.
The deliverable is an OCR transcription archived under `archive/` plus the
metadata needed by the rest of the workflow (summary page, typed pages,
unknowns, log entry).  Validated end-to-end in the romania-news wiki on the SNDD-1999 case
(114-page WorkCentre photocopy scan; see that wiki's
`wiki/log/20261004T193028+0300.md`).

## When to use

Trigger phrases: **"ingest this PDF"**, **"OCR this file"**, a bare
scanned-document URL (e.g. a `cndd.ro/wp-content/uploads/...pdf` reference from
a news piece) in an ingest request, or **any PDF whose `pdftotext` probe
returns a near-empty text layer** (rule of thumb: `< 2 KB total or < ~150
B/page` — the bundled script applies this test automatically).

Do **NOT** fire for:

- Ordinary HTML articles (the webfetch branch of the ingest workflow).
- Video URLs (`youtube-transcript` skill).
- PDFs with a healthy text layer — copy the `pdftotext` output into the
  archive instead; do not OCR.

## Preconditions

On PATH: `curl`, `pdftoppm`/`pdftotext`/`pdfinfo` (poppler-utils), and
`tesseract` with the **wiki language's pack** (`ron` for a Romanian
wiki, `eng` for English).  Verify with:

```
tesseract --list-langs      # must list the wiki language, e.g. ron
```

**Self-hosting fallback** (no sudo): download the Ubuntu .debs and extract
them with `dpkg -x` into a temp prefix (validated in-session; swap
`tesseract-ocr-ron` for the pack your wiki's language needs):

```
mkdir -p /tmp/opencode/tess && cd /tmp/opencode/tess
apt-get download tesseract-ocr tesseract-ocr-ron tesseract-ocr-eng libtesseract5 liblept5
for d in *.deb; do dpkg -x "$d" prefix/; done
export LD_LIBRARY_PATH=/tmp/opencode/tess/prefix/usr/lib/x86_64-linux-gnu
TESSDATA_PREFIX=/tmp/opencode/tess/prefix/usr/share/tesseract-ocr/5/tessdata \
  /tmp/opencode/tess/prefix/usr/bin/tesseract --list-langs
```

If a pack is missing (`tesseract-ocr-ron`), ask the user to install it —
`--user` pip packages do not carry the binary (`externally-managed-environment`
blocks the tesseract binary path).

## Procedure

### Step 1 — download + text-layer probe

Run the bundled pipeline — `scripts/ocr_pipeline.sh`, relative to this
skill's directory (per-wiki OpenCode copies keep their `.opencode/`
prefix) — passing the URL or local path:

```
scripts/ocr_pipeline.sh \
  <URL-or-path> [workdir=/tmp/ocr-XXXX] [dpi=200] [langs=ron] [psm=3] [workers=4]
```

Outputs in the workdir: `source.pdf`, `ocr/p-NNN.tif` (200 DPI greyscale),
`ocr/full.txt` (assembled, with `===== PAGE N =====` markers), `ocr.done`
sentinel.  A toolchain-missing run fails fast at `tesseract` / `pdftoppm` —
go back to Preconditions.

Parameter notes: 200 DPI + greyscale is the WorkCentre-scan sweet spot;
raise to 300 DPI for sub-300 DPI originals (fax-grade).  For mixed-language
docs use `ron+eng`.  A government-booklet scan produced ~4.3 kB/page.

### Step 2 — read the transcription and pin the document identity

Read `ocr/full.txt` (pages 1-3 usually carry the cover, copyright page and
first preface — that is where the publication house, ISBN/ISSN, copyright
holder and internal date live).  Extract:

- full title, publisher, year, ISBN/printing data;
- the crediting/authorship structure **as printed** (drafting groups,
  promotion instruments, HG/GD numbers) — this is the load-bearing part when
  the later press shorthand diverges from the primary document;
- prefaces and their signatories (signatures come out as glyphs — note them,
  do not trust them as clean names);
- the document's internal page-numbering span vs the scan's page count
  (a front-matter offset is expected and must be recorded).

### Step 3 — archive

Copy the **original PDF** and the **OCR transcription** (provenance header +
the page-marked text) into the repo:

```
archive/YYYY/MM/DD/<slug>-original.pdf      # retrieval-date scan (IMMUTABLE: never edit)
archive/YYYY/MM/DD/<slug>-ocr.md            # provenance header + full text
```

Provenance header must state: original title/publisher/year/ISBN, the PDF
URL, the scan/toolchain provenance (tool, language pack, DPI, PSM, date),
the page-marker convention, the OCR-error register (with examples), and the
front-matter/page-offset caveat.  Date the folder by **retrieval** for
document-era scans unless the internal date is pinned with an adopting
instrument (HG/GD) — internal year goes in the header either way.

### Step 4 — discuss takeaways BEFORE writing anything

Per `AGENTS.md` §"Ingest workflow" step 3: present key takeaways
(document identity, credits/authorship structure, how the primary document
refines or contradicts the wiki's current framing) and ask the user for
ingest scope.  Handle the answer with the standard footprint:
summary page + typed-page extensions + unknowns + indexes + log.

### Step 5 — record OCR limits as an unknown

Any machine transcription gets one `wiki/unknowns.md` entry: character-slip
examples, page-offset math, machine-read signature glyphs, and the rule
that content claims cite the OCR text with recorded limits
(see the SNDD-1999 entry for the template).  Add it to the _Stated in_
lists of any page stating OCR-derived facts.

### Step 6 — log, via the skill

Close with the `write-log-entry` skill (frontmatter `Sources:` must list
both archived files, the summary, and every extended page).

## Quality register (romania-news SNDD-1999 reference)

- 200 DPI / greyscale / `ron` / PSM 3: ~4.3 kB/page on dense text, fully
  usable; slips are per-character not per-word.
- Signatures/handwriting: never usable (record as machine-read glyphs).
- Small-caps headers and diacritic variants are the common error classes;
  they matter only when a wiki page quotes the exact glyph.

## Related

- `youtube-transcript` skill — transcript-branch sibling for video sources;
  the provenance-header and archive conventions match.
- `write-log-entry` skill — mandatory close-out.
- AGENTS.md §"Ingest workflow", §"The wiki/unknowns.md file".
