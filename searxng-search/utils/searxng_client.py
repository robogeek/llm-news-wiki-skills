import urllib.parse
import urllib.request
import json

DEFAULT_BASE = "https://searxng-ai-nuc3.tailbedcb3.ts.net"

COUNTRY_LANG = {
    "ro": "ro", "md": "ro", "gr": "el", "cy": "el", "bg": "bg", "hu": "hu",
    "ua": "uk", "de": "de", "at": "de", "ch": "de", "fr": "fr", "be": "fr",
    "it": "it", "es": "es", "pt": "pt", "gb": "en", "uk": "en", "ie": "en",
    "us": "en", "pl": "pl", "cz": "cs", "sk": "cs", "se": "sv", "dk": "da",
    "no": "nb", "fi": "fi", "nl": "nl", "tr": "tr", "rs": "sr", "hr": "hr",
    "si": "sl", "il": "he", "ae": "ar", "eg": "ar",
}

def build_query(terms, sites, exact):
    """Compose the q string: terms (optionally quoted) plus site: filters."""
    if isinstance(terms, str):
        terms = [terms]
    parts = []
    for t in terms:
        parts.append(f'"{t}"' if exact and " " in t else t)
    q = " ".join(parts)
    if sites:
        if isinstance(sites, str):
            sites = [sites]
        site_expr = " OR ".join(f"site:{s}" for s in sites)
        q = f"{q} {site_expr}" if q else site_expr
    return q

def resolve_lang(tag):
    if tag is None:
        return None
    t = tag.strip().lower().replace("-", "")
    if t in COUNTRY_LANG:
        return COUNTRY_LANG[t]
    return tag

def fetch(base, params, timeout):
    qs = urllib.parse.urlencode(params)
    url = f"{base}/search?{qs}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; searxng-search-skill)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8", "replace")
    if "json" not in ctype:
        raise RuntimeError(
            f"non-JSON response (content-type: {ctype!r}) - wrong endpoint or "
            f"format=json disabled on the instance"
        )
    return json.loads(body)
