#!/usr/bin/env bash
# OCR pipeline for scanned PDFs (news-wiki ingest).
# Usage:
#   ocr_pipeline.sh <pdf-url-or-local-path> [workdir] [dpi] [lang] [psm] [workers]
# Produces in <workdir>:
#   source.pdf      — the downloaded (or copied) original
#   ocr/p-NNN.tif   — 200 DPI greyscale page images
#   ocr/full.txt    — assembled per-page OCR text with ===== PAGE N ===== markers
#   ocr.done        — sentinel written on success
# Requirements on PATH: curl, pdftoppm (poppler-utils), tesseract + a language pack
# (check with: tesseract --list-langs). pdftotext/PDFinfo from poppler too.
set -euo pipefail

URL_OR_PATH_IN="${1:?usage: ocr_pipeline.sh <pdf-url-or-local-path> [workdir] [dpi] [lang] [psm] [workers]}"
WORKDIR="${2:-$(mktemp -d /tmp/ocr-XXXXXX)}"
DPI="${3:-200}"
LANGS="${4:-ron}"
PSM="${5:-3}"
WORKERS="${6:-4}"

# resolve local paths to absolute BEFORE cd'ing into the workdir
if [[ -f "$URL_OR_PATH_IN" ]]; then
  URL_OR_PATH=$(readlink -f "$URL_OR_PATH_IN")
else
  URL_OR_PATH="$URL_OR_PATH_IN"
fi

mkdir -p "$WORKDIR/ocr"
cd "$WORKDIR"

# 1) fetch or copy
if [[ -f "$URL_OR_PATH" ]]; then
  cp "$URL_OR_PATH" source.pdf
else
  curl -L -sS --max-time 120 -o source.pdf "$URL_OR_PATH"
fi
file source.pdf | grep -qi pdf || { echo "NOT A PDF: $(file source.pdf)" >&2; exit 1; }

# 2) text layer probe — skip OCR when a real text layer exists
pages=$(pdfinfo source.pdf | awk '/^Pages:/{print $2}')
pdftotext -layout source.pdf probe.txt 2>/dev/null || true
probe_bytes=$(wc -c < probe.txt 2>/dev/null || echo 0)
# crude rule: >2 KB and over ~150 B/page means a text layer is present
if [[ "$probe_bytes" -gt 2000 && "$probe_bytes" -gt $((pages * 150)) ]]; then
  echo "TEXT LAYER PRESENT ($probe_bytes bytes / $pages pages) — use pdftotext output, no OCR needed."
  mv probe.txt ocr/full.txt
  echo "$probe_bytes bytes; TEXT-LAYER PATH (no OCR)." > ocr.done
  echo "DONE (text layer) $WORKDIR"
  exit 0
fi
echo "No usable text layer ($probe_bytes bytes / $pages pages) — OCR required."

# 3) rasterize
pdftoppm -gray -r "$DPI" -tiff source.pdf ocr/p

# 4) OCR in parallel
cd ocr
ls p-*.tif 2>/dev/null | head -1 >/dev/null || { echo "pdftoppm produced no pages?" >&2; exit 1; }
ls p-*.tif | sort -V | xargs -P "$WORKERS" -I{} bash -c \
  'b="{}"; b=${b%.tif}; tesseract "$b.tif" "$b" -l '"$LANGS"' --psm '"$PSM"' 2>/dev/null'

# 5) assemble with page markers (order = page order via zero-padded names)
: > full.txt
i=0
for f in $(ls p-*.txt | sort -V); do
  i=$((i+1))
  printf '\n\n===== PAGE %d =====\n\n' "$i" >> full.txt
  cat "$f" >> full.txt
done

cd ..
echo "$pages pages; langs=$LANGS; dpi=$DPI" > ocr.done
bytes=$(wc -c < ocr/full.txt)
echo "DONE $WORKDIR"
echo "full.txt: $bytes bytes for $pages pages"
