#!/usr/bin/env python3
"""
Scrape IPO list from e-IPO (list view) into CSV + JSON.

Source list view is paginated like:
https://e-ipo.co.id/id/ipo/index?page=N&per-page=12&view=list
(captured from the site's pagination behavior)
"""

from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag


BASE = "https://e-ipo.co.id"
LIST_URL = f"{BASE}/id/ipo/index"


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class IPOItem:
    company_name: str
    ticker: Optional[str]
    status: Optional[str]
    sector: Optional[str]
    sharia: bool
    listing_date: Optional[str]          # "17 Dec 2025" style (site format)
    bookbuilding_period: Optional[str]   # "09 Dec 2020 - 17 Dec 2020" style
    final_price: Optional[str]           # "Rp 635" style
    bookbuilding_price_range: Optional[str]  # "Rp 298 - Rp 328" style
    shares_offered_lot: Optional[str]    # "44.066.123 Lot" style
    detail_url: Optional[str]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_ticker(title: str) -> Tuple[str, Optional[str]]:
    """
    Title format typically: "PT Super Bank Indonesia Tbk (SUPA)"
    """
    m = re.match(r"^(.*)\(([^()]+)\)\s*$", title.strip())
    if not m:
        return title.strip(), None
    return m.group(1).strip(), m.group(2).strip()


def _kv_from_card_text(card: Tag) -> Dict[str, str]:
    """
    Cards show label/value pairs like:
      'Sektor' -> 'Financials'
      'Tanggal Pencatatan' -> '17 Dec 2025'
      'Harga Final' -> 'Rp 635'
      'Saham Ditawarkan' -> '44.066.123 Lot'
    or (for some statuses):
      'Periode Book Building' -> '09 Dec 2020 - 17 Dec 2020'
      'Rentang Harga Book Building' -> 'Rp 298 - Rp 328'
    """
    text = _clean(card.get_text(" ", strip=True))

    # Known labels (Indonesian) appearing in list cards
    labels = [
        "Sektor",
        "Tanggal Pencatatan",
        "Harga Final",
        "Saham Ditawarkan",
        "Periode Book Building",
        "Rentang Harga Book Building",
    ]

    # Build regex that slices values between labels
    # Example: Sektor (value...) Tanggal Pencatatan (value...) Harga Final (value...)
    escaped = [re.escape(x) for x in labels]
    splitter = r"(" + "|".join(escaped) + r")"

    parts = re.split(splitter, text)
    # parts looks like: [prefix, label, after, label, after, ...]
    kv: Dict[str, str] = {}
    i = 1
    while i < len(parts) - 1:
        label = parts[i]
        after = parts[i + 1]
        # value ends at next label occurrence; since split already, 'after' may include other content
        # trim any leading punctuation or stray tokens
        value = after.strip(" -:|")
        kv[label] = value
        i += 2

    return kv


def _find_status_near_title(h3: Tag) -> Optional[str]:
    """
    The status often appears right after the title (e.g., Closed, Canceled, etc.).
    We'll scan forward within the same card container for a short badge-like text.
    """
    card = h3.find_parent(["article", "div", "li", "section"])
    if not card:
        return None

    # Look for short tokens commonly used as status (capitalize, 1 word)
    candidates = []
    for t in card.stripped_strings:
        s = _clean(t)
        if s in {"Pre-Effective", "Book Building", "Waiting For Offering", "Offering",
                 "Allotment", "Closed", "Postpone", "Canceled"}:
            candidates.append(s)

    # Usually the first match is the status
    return candidates[0] if candidates else None


def _has_sharia(card: Tag) -> bool:
    # "Syariah" appears as a token inside some cards.
    return "Syariah" in set(_clean(x) for x in card.stripped_strings)


def _find_detail_url(card: Tag) -> Optional[str]:
    # "Info lebih lanjut" link is present on each card.
    a = card.find("a", string=re.compile(r"Info lebih lanjut", re.IGNORECASE))
    if not a or not a.get("href"):
        return None
    href = a["href"].strip()
    if href.startswith("http"):
        return href
    return BASE + href


def fetch_page(session: requests.Session, page: int, per_page: int = 12) -> str:
    params = {"page": page, "per-page": per_page, "view": "list"}
    r = session.get(LIST_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def parse_items(html: str) -> List[IPOItem]:
    soup = BeautifulSoup(html, "html.parser")

    # Titles show up as <h3> in list view.
    h3s = soup.find_all("h3")
    # Filter to likely IPO titles: contains "(TICKER)" or at least "PT "
    titles = []
    for h3 in h3s:
        t = _clean(h3.get_text(" ", strip=True))
        if not t:
            continue
        if "PT " in t or re.search(r"\([A-Z0-9]{3,5}\)$", t):
            titles.append(h3)

    items: List[IPOItem] = []

    for h3 in titles:
        title_text = _clean(h3.get_text(" ", strip=True))
        company, ticker = _extract_ticker(title_text)

        card = h3.find_parent(["article", "div", "li", "section"])
        if not card:
            continue

        status = _find_status_near_title(h3)
        sharia = _has_sharia(card)
        kv = _kv_from_card_text(card)

        sector = kv.get("Sektor")
        listing_date = kv.get("Tanggal Pencatatan")
        final_price = kv.get("Harga Final")
        shares_offered = kv.get("Saham Ditawarkan")
        bb_period = kv.get("Periode Book Building")
        bb_range = kv.get("Rentang Harga Book Building")
        detail_url = _find_detail_url(card)

        items.append(
            IPOItem(
                company_name=company,
                ticker=ticker,
                status=status,
                sector=sector,
                sharia=sharia,
                listing_date=listing_date,
                bookbuilding_period=bb_period,
                final_price=final_price,
                bookbuilding_price_range=bb_range,
                shares_offered_lot=shares_offered,
                detail_url=detail_url,
            )
        )

    # De-dup within page (sometimes layout repeats or nested containers cause duplicates)
    seen = set()
    uniq: List[IPOItem] = []
    for it in items:
        key = (it.company_name, it.ticker, it.detail_url)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)

    return uniq


def scrape_all(max_pages: int = 200, sleep_s: float = 0.7) -> List[IPOItem]:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "id,en;q=0.9"})

    all_items: List[IPOItem] = []
    for page in range(1, max_pages + 1):
        html = fetch_page(session, page=page)
        items = parse_items(html)

        if not items:
            # Stop when pagination runs out.
            break

        all_items.extend(items)
        time.sleep(sleep_s)

    # Global de-dup
    seen = set()
    uniq: List[IPOItem] = []
    for it in all_items:
        key = (it.company_name, it.ticker, it.detail_url)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)

    return uniq


def write_csv(path: str, items: List[IPOItem]) -> None:
    fieldnames = list(asdict(items[0]).keys()) if items else [f.name for f in IPOItem.__dataclass_fields__.values()]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for it in items:
            w.writerow(asdict(it))


def write_json(path: str, items: List[IPOItem]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in items], f, ensure_ascii=False, indent=2)


import time
import requests

BASE = "https://e-ipo.co.id"
LIST_URL = f"{BASE}/id/ipo/index"

def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": BASE + "/id",
    })
    return s

def warmup(s: requests.Session) -> None:
    # Hit homepage first to receive cookies/session
    r = s.get(BASE + "/id", timeout=30)
    r.raise_for_status()
    time.sleep(0.5)

def fetch_page(s: requests.Session, page: int, per_page: int = 12) -> str:
    params = {"page": page, "per-page": per_page, "view": "list"}
    r = s.get(LIST_URL, params=params, timeout=30)
    if r.status_code == 403:
        raise RuntimeError(
            "403 blocked. Site likely requires JS/cookies/WAF challenge. "
            "Use Playwright approach (Option B)."
        )
    r.raise_for_status()
    return r.text

if __name__ == "__main__":
    s = new_session()
    warmup(s)
    html = fetch_page(s, 1)
    print("OK len(html)=", len(html))
