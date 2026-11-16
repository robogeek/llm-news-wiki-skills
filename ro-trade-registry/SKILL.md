---
name: ro-trade-registry
description: "Look up a Romanian entity in the trade-registry mirrors (TotalFirme.ro / Metricbiz.ro) by CUI or name: founding date, legal status, fiscal-inactivity flag, seat, financial indicators, state debts and insolvency risk. Use when a wiki page needs an entity's registration data (launch date, status, finances) - e.g. \"find the launch date of X\", \"look up CUI NNNN\", \"is X still active\". Pairs with the searxng-search skill for the discovery step."
---

# Romanian trade-registry lookup (TotalFirme.ro / Metricbiz.ro)

Retrieves a Romanian entity's trade-registry record — **founding date, legal
status, fiscal-inactivity flag, seat, financial indicators, state debts,
insolvency risk** — from the public registry mirrors. Discovered 29 October
2026 while resolving the Fundația Centrul româno-american launch date
(founded **12 June 2003**, CUI 15506155 — predating the 2012 ALO).

## Why this skill exists

The wiki frequently needs an entity's **launch date** and **activity record**
(see the Fundația and "41 pentru România" lookups). The official registry
data is mirrored by several public sites; **TotalFirme.ro is the one that is
server-rendered** (parseable without JavaScript). Metricbiz.ro mirrors the
same data but is a JS-rendered SPA (only the canonical URL is in the HTML —
useless via curl). ListaInstitutii.ro is likewise an Angular shell.

## The URL patterns

- **TotalFirme**: `https://www.totalfirme.ro/{name-slug}-{CUI}`
  (e.g. `fundatia-centrul-romano-american-15506155`) — **no CUI-only or
  search endpoint works** (probed: `/cui/NNN`, `/cauta?q=`, `/search?q=`,
  `/firme/cui/NNN` all 404).
- **Metricbiz**: `https://metricbiz.ro/firma/{name-slug}-cui-{CUI}` — a
  CUI-only form (`/firma/cui-{CUI}`) returns 200 but is a JS shell.

**Consequence**: the slug is required, so the discovery step is a **web
search** — the totalfirme/metricbiz URLs surface in results for the entity
name (proven: the SearXNG engine-routed fallback returned the TotalFirme URL
for "Fundația Centrul româno-american" on the first try).

## The workflow (as automated in `scripts/cui_lookup.py`)

```
python3 scripts/cui_lookup.py --cui 15506155 --name "Fundația Centrul româno-american"
python3 scripts/cui_lookup.py --cui 15506155 --url https://www.totalfirme.ro/fundatia-centrul-romano-american-15506155
python3 scripts/cui_lookup.py --name "SC Example SRL" --json
```

1. **URL discovery** (skipped when `--url` is given): search for the entity
   via SearXNG (engine-routed: `bing,yahoo,yandex,seznam,yep,qwant` — the
   big four are often runtime-suspended) and, if needed, OpenSerp
   (google/bing/duckduckgo). Query shapes tried in order:
   `"{name}" {cui}`, `{cui} totalfirme`, `"{name}" site:totalfirme.ro`.
   Accept only URLs on totalfirme.ro / metricbiz.ro whose path contains the
   CUI digits.
2. **Fetch** the TotalFirme page (prefer it over Metricbiz).
3. **Parse** (regex on the tag-stripped text): the entity name, CUI
   verification (the page must contain the requested CUI — mismatch = wrong
   entity, stop), `Dată înființare`, `În funcțiune din ...`, `Inactiv fiscal
   din ...`, `Sediu social`, the financial-table years, `Datorii la stat`,
   `Risc insolvență`, BPI presence.
4. **Report** the fields + the source URL (always cite it — the data is
   open-government licensed but dated: TotalFirme stamps its last update).

## Fields available on a TotalFirme record

- **Dată înființare** / **Stare firmă (În funcțiune din ...)** — the launch
  date and legal status
- **Inactiv fiscal din ...** — the fiscal-deactivation flag (important: an
  entity can be "În funcțiune" at the registry yet fiscally inactive)
- **Sediu social** — the registered seat (compare against any OSIM/filing
  address — a mismatch is a verification flag)
- **Financial indicators** (balance sheets filed at the Ministry of Finance,
  per year): revenue, expenses, profit, employees, equity, debts — the
  **activity record in the negative** (zero revenue for years = dormant)
- **Datorii la stat** (state debts, with date), **Risc insolvență** (%),
  **BPI** presence (insolvency proceedings)

## Caveats (learned 29 October 2026)

- **Entity identity must be verified**: the name match is not proof — check
  the CUI on the page, and compare the seat against other records (the
  Fundația's registry seat, Str. Avrig 28, differed from its OSIM filing
  address, Casa Vernescu). Record the caveat in the wiki page.
- **Name collisions are heavy**: "Centrul româno-american" pulls in the
  unrelated Romanian-American Foundation and the RAU university cluster.
  The CUI is the only reliable key.
- **The data is dated** — TotalFirme stamps its last update; cite the
  retrieval date in the wiki.
- **An entity can be registry-active but fiscally inactive** — both fields
  matter (the Fundația: "În funcțiune din 12.06.2003" yet "Inactiv fiscal
  din 03.09.2024").
- **The founding act is not in these mirrors** — the curtors and registering
  court need the MoJ NGO registry or the tribunal file.
- If the search layer is down entirely, fall back to asking the user for the
  direct TotalFirme URL, or try `metricbiz.ro/firma/cui-{CUI}` in a real
  browser (JS-rendered).

## From record to wiki

Cite the mirror URL as the source (open-government licence), **with the
retrieval date**; register any identity caveat in `wiki/unknowns.md`; the
financial table can be condensed into the wiki page (see the Fundația
page's registry section for the format).
