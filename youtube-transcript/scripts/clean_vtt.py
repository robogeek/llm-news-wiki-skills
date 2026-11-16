#!/usr/bin/env python3
"""clean_vtt.py - convert a (YouTube) WebVTT caption file to clean running text.

Handles both manually-authored captions and auto-generated ("ro-orig" style)
captions:

  * strips WebVTT headers, cue timing lines, and inline karaoke tags <..*..>
  * un-escapes HTML entities (&gt; &amp; &lt;)
  * merges YouTube's rolling-window auto-caption cues (each cue repeats the tail
    of the previous window) via longest suffix/prefix matching
  * turns ">>" speaker-change markers into paragraph breaks
  * collapses whitespace and pulls punctuation tight against words

Usage:
    python3 clean_vtt.py INPUT.vtt [-o OUTPUT.txt]

Prints the cleaned transcript to stdout (or OUTPUT.txt) and a short stats
line to stderr.  Manual captions (no overlap between cues) pass through the
same merge harmlessly.

Auto-caption text still contains ASR errors (garbled names, dropped digits).
The script does NOT attempt to correct content - flag suspected artifacts in
the archive file header instead.
"""
import argparse
import re
import sys


def parse_cues(path):
    cues = []
    cur = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
                continue
            if "-->" in line:
                if cur:
                    cues.append(cur)
                cur = []
                continue
            if cur is None:
                continue
            clean = re.sub(r"<[^>]+>", "", line)  # karaoke + styling tags
            clean = (clean.replace("&gt;", ">").replace("&lt;", "<")
                          .replace("&amp;", "&").strip())
            if clean:
                cur.append(clean)
    if cur:
        cues.append(cur)
    return [" ".join(w) for w in cues if w]


def merge_rolling(cues):
    """Merge overlapping rolling-caption windows by longest suffix/prefix match."""
    if not cues:
        return []
    merged = cues[0].split()
    for cue in cues[1:]:
        words = cue.split()
        k = 0
        for cand in range(min(len(merged), len(words)), 0, -1):
            if merged[-cand:] == words[:cand]:
                k = cand
                break
        merged.extend(words[k:])
    return merged


def render(words):
    text = " ".join(words)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)      # punctuation tight
    text = text.replace(">>", "\n\n>> ")               # speaker markers
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input .vtt file")
    ap.add_argument("-o", "--output", help="output text file (default: stdout)")
    args = ap.parse_args()

    cues = parse_cues(args.input)
    text = render(merge_rolling(cues))
    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    out.write(text + "\n")
    if args.output:
        out.close()
    print(f"{len(cues)} cues -> {len(text.split())} words, {len(text)} chars",
          file=sys.stderr)


if __name__ == "__main__":
    main()
