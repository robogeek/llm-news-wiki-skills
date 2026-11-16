#!/usr/bin/env python3
"""Look up a Romanian entity in the trade-registry mirrors (TotalFirme.ro).

Built for the ro-trade-registry skill (news-wiki toolkit). Given a CUI
(optionally with the entity name), discovers the TotalFirme.ro record URL
via web search (SearXNG engine-routed + OpenSerp fallback), fetches the
server-rendered page, and extracts the registry fields: founding date,
legal status, fiscal-inactivity flag, seat, financial-table years, state
debts, insolvency risk, BPI presence.

Discovered 29 October 2026 resolving the Fundația Centrul româno-american
launch date (founded 12 June 2003, CUI 15506155).

Examples:
  cui_lookup.py --cui 15506155 --name "Fundația Centrul româno-american"
  cui_lookup.py --cui 15506155 --url https://www.totalfirme.ro/fundatia-centrul-romano-american-15506155
  cui_lookup.py --name "SC Example SRL" --json
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

DEFAULT_SEARXNG = "https://searxng-ai-nuc3.tailbedcb3.ts.net"
DEFAULT_OPENSERP = "https://openserp.tailbedcb3.ts.net"
FALLBACK_ENGINES = "bing,yahoo,yandex,seznam,yep,qwant"
UA = "Mozilla/5.0 (compatible; ro-trade-registry-skill)"


def http_get(url, timeout, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def searxng_search(base, q, timeout, engines=FALLBACK_ENGINES):
    params = urllib.parse.urlencode(
        {"q": q, "format": "json", "categories": "general", "pageno": 1,
         "engines": engines})
    try:
        data = json.loads(http_get(f"{base}/search?{params}", timeout))
        return data.get("results", [])
    except Exception as e:  # noqa: BLE001
        print(f"#   searxng error: {e}", file=sys.stderr)
        return []


def openserp_search(base, q, timeout, engine="google", limit=10):
    params = urllib.parse.urlencode({"text": q, "limit": limit})
    try:
        data = json.loads(http_get(f"{base}/{engine}/search?{params}", timeout))
        return data if isinstance(data, list) else data.get("results", [])
    except Exception as e:  # noqa: BLE001
        print(f"#   openserp error: {e}", file=sys.stderr)
        return []


def strip_tags(html):
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def norm(s):
    """Normalize Romanian diacritic variants (ț/ț->t, ș/ș->s, ă->a, î/î->i)
    so pattern matching survives the sites' mixed encoding."""
    s = s.replace("\u021b", "t").replace("\u021a", "T")
    s = s.replace("\u0219", "s").replace("\u0218", "S")
    s = s.replace("\u0103", "a").replace("\u0102", "A")
    s = s.replace("\u00ee", "i").replace("\u00ce", "I")
    s = s.replace("\u00e3", "a").replace("\u00c3", "A")
    return s


def discover_url(cui, name, searxng_base, openserp_base, timeout):
    """Find the TotalFirme/Metricbiz URL for the entity via web search."""
    cui_digits = re.sub(r"\D", "", cui or "")
    queries = []
    if name:
        queries.append(name)  # bare name first - the proven shape (29 Oct 2026)
        queries.append(f"{name} totalfirme")
        queries.append(f'"{name}" {cui_digits}')
    queries.append(f"{cui_digits} totalfirme")
    candidates = []
    for q in queries:
        for r in searxng_search(searxng_base, q, timeout):
            candidates.append(r.get("url") or "")
        for r in openserp_search(openserp_base, q, timeout, "google"):
            candidates.append(r.get("url") or "")
        for u in candidates:
            if re.search(r"totalfirme\.ro|metricbiz\.ro", u) and cui_digits in u.replace("-", ""):
                return u
        candidates = []
    # last pass: accept any totalfirme/metricbiz URL containing the CUI digits
    for q in queries[:2]:
        for r in searxng_search(searxng_base, q, timeout):
            u = r.get("url") or ""
            if re.search(r"totalfirme\.ro|metricbiz\.ro", u) and cui_digits in u.replace("-", ""):
                return u
    return None


def parse_record(html, cui):
    """Extract the registry fields from a TotalFirme page."""
    cui_digits = re.sub(r"\D", "", cui or "")
    text = strip_tags(html)
    ntext = norm(text)  # diacritic-normalized copy for pattern matching
    out = {"cui_requested": cui_digits,
           "cui_on_page": cui_digits if cui_digits in text.replace("-", "").replace(" ", "") else None}
    m = re.search(r"(FUNDATI[ĂA]|SOCIETATE|S\.C\.|SC)[^|]{0,120}?ROMANO-AMERICAN", text, re.I)
    name = re.search(r"<title>([^<]+)</title>", html)
    out["page_title"] = name.group(1).strip() if name else None
    m = re.search(r"Data infiintare:?\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", ntext, re.I)
    if not m:
        m = re.search(r"infiintare:?\s*([0-9]{1,2}\.?[0-9]{0,2}\.?[0-9]{4}|[0-9]{1,2}\s+\w+\s+[0-9]{4})", ntext, re.I)
    out["founding_date"] = m.group(1).strip() if m else None
    m = re.search(r"In functiune\s*din\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", ntext, re.I)
    out["status_active_since"] = m.group(1) if m else None
    m = re.search(r"Inactiv fiscal\s*din\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", ntext, re.I)
    out["fiscally_inactive_since"] = m.group(1) if m else None
    m = re.search(r"Sediu social:\s*([A-ZĂÂÎȘȚ0-9][^|]{10,160}?)(?:Vezi|Cod|Judet|Județ|$)", text)
    out["seat"] = m.group(1).strip(" ,") if m else None
    m = re.search(r"Are\s+([0-9.,]+)\s*RON\s+datorii c[aă]tre stat la\s+([0-9.]+)", ntext, re.I)
    if m:
        out["state_debt"] = f"{m.group(1)} RON at {m.group(2)}"
    m = re.search(r"Risc insolventa\s*:?((?:\s*\S+){0,12}?[0-9]+%)", ntext, re.I)
    out["insolvency_risk"] = (m.group(1).strip() if m else None)
    if re.search(r"nu\s+apare\s+in\s+BPI", ntext, re.I):
        out["in_bpi"] = False
    elif re.search(r"apare\s+in\s+BPI", ntext, re.I):
        out["in_bpi"] = True
    else:
        out["in_bpi"] = None
    years = re.findall(r"\b(20[0-2][0-9])\b", text[: len(text) // 3])
    out["financial_years_mentioned"] = sorted(set(years), reverse=True)[:10]
    out["has_financial_table"] = "Profit brut" in ntext
    return out


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cui", help="the entity's CUI (digits)")
    p.add_argument("--name", help="entity name (helps URL discovery)")
    p.add_argument("--url", help="direct TotalFirme URL (skips discovery)")
    p.add_argument("--searxng-base", default=DEFAULT_SEARXNG)
    p.add_argument("--openserp-base", default=DEFAULT_OPENSERP)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if not a.cui and not a.name and not a.url:
        p.error("provide --cui and/or --name, or --url")

    url = a.url
    if not url:
        print(f"# discovering URL for CUI {a.cui or '?'} / name: {a.name or '?'} ...",
              file=sys.stderr)
        url = discover_url(a.cui, a.name, a.searxng_base, a.openserp_base, a.timeout)
    if not url:
        print("# URL not found. Try: the direct TotalFirme URL, or "
              "metricbiz.ro/firma/cui-{CUI} in a browser (JS-rendered).")
        return 1
    print(f"# source: {url}")
    html = http_get(url, a.timeout)
    rec = parse_record(html, a.cui or "")
    rec["source_url"] = url
    if a.cui and rec["cui_on_page"] is None:
        print(f"# WARNING: requested CUI {a.cui} not found on the page - "
              f"possible wrong entity; verify before citing.", file=sys.stderr)
        rec["identity_warning"] = "requested CUI not found on page"
    if a.json:
        json.dump(rec, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    print(f"# entity page title: {rec['page_title']}")
    print(f"# CUI on page: {rec['cui_on_page'] or 'NOT FOUND - verify!'}")
    print(f"# founding date: {rec['founding_date'] or 'not parsed'}")
    print(f"# status active since: {rec['status_active_since'] or 'not parsed'}")
    print(f"# fiscally inactive since: {rec['fiscally_inactive_since'] or '(not flagged)'}")
    print(f"# seat: {rec['seat'] or 'not parsed'}")
    print(f"# state debt: {rec.get('state_debt') or 'not parsed'}")
    print(f"# insolvency risk: {rec['insolvency_risk'] or 'not parsed'}")
    print(f"# in BPI (insolvency bulletin): {rec['in_bpi']}")
    print(f"# financial table present: {rec['has_financial_table']} "
          f"(years: {', '.join(rec['financial_years_mentioned']) or '-'})")
    print("# read the full record at the source URL above.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
