"""Shared parsing utilities for templates.

Provides a minimal set of helpers for JSON-LD extraction, microdata
and meta tag fallbacks, and a single `make_soup` helper so pages are
parsed consistently.
"""
from typing import List, Dict, Any, Optional
import json
import html as _html
import re
from bs4 import BeautifulSoup


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'lxml')


def extract_jsonld_objects(html: str) -> List[Dict[str, Any]]:
    soup = make_soup(html)
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all('script', type='application/ld+json'):
        raw = tag.string or ''
        # try simple json loads first
        try:
            data = json.loads(_html.unescape(raw))
        except Exception:
            # try to extract a JSON object from an assignment (window.__STATE__ = {...})
            m = re.search(r'={1}\s*({[\s\S]+})', raw)
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    continue
            else:
                continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    out.append(item)
        elif isinstance(data, dict):
            out.append(data)

    return out


def extract_meta_values(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    def meta(name=None, prop=None):
        if prop:
            tag = soup.find('meta', attrs={'property': prop})
            if tag and tag.get('content'):
                return tag['content']
        if name:
            tag = soup.find('meta', attrs={'name': name})
            if tag and tag.get('content'):
                return tag['content']
        return None

    out: Dict[str, Optional[str]] = {}
    out['title'] = meta(prop='og:title') or meta(name='title') or (soup.title.string if soup.title else None)
    out['price'] = meta(prop='product:price:amount') or meta(name='price')
    out['currency'] = meta(prop='product:price:currency') or meta(name='currency')
    out['description'] = meta(prop='og:description') or meta(name='description')
    return out


def extract_microdata(html: str) -> List[Dict[str, Any]]:
    soup = make_soup(html)
    results: List[Dict[str, Any]] = []
    for tag in soup.find_all(attrs={"itemscope": True}):
        it = tag.get('itemtype') or ''
        # basic filter for vehicle microdata
        if 'vehicle' in it.lower():
            out: Dict[str, Any] = {}
            for prop in ('name', 'brand', 'model', 'description', 'price'):
                node = tag.find(attrs={'itemprop': prop})
                if node:
                    # prefer content attribute for meta-like tags
                    if node.name == 'meta' and node.get('content'):
                        out[prop] = node['content']
                    else:
                        out[prop] = node.get_text(strip=True)
            price_meta = tag.find('meta', attrs={'itemprop': 'price'})
            if price_meta and price_meta.get('content'):
                out['price'] = price_meta['content']
            results.append(out)
    return results


def parse_price(txt: Optional[str]):
    """Try to parse a price string into (amount: float|None, currency: str|None).

    This is a lightweight normalizer: strips common currency symbols and
    thousands separators, handles simple currency codes (GBP, USD, EUR).
    Returns (None, None) on failure.
    """
    if not txt:
        return None, None
    s = str(txt).strip()
    # common currency symbols
    cur = None
    # detect currency code like GBP, USD
    m_code = re.search(r"\b(GBP|USD|EUR|AUD|CAD|JPY|CHF)\b", s, re.I)
    if m_code:
        cur = m_code.group(1).upper()
    # common symbols
    if s.startswith('£'):
        cur = cur or 'GBP'
        s = s.lstrip('£')
    if s.startswith('$'):
        cur = cur or 'USD'
        s = s.lstrip('$')
    if s.startswith('€'):
        cur = cur or 'EUR'
        s = s.lstrip('€')

    # remove currency letters/symbols intermixed
    s = re.sub(r"[A-Za-z£$€¥,\s]+", lambda m: '' if any(c.isdigit() for c in m.group(0)) else '', s)
    # fallback: strip non-digit except dot
    s = re.sub(r"[^0-9\.\-]", '', s)
    if not s:
        return None, cur
    try:
        amt = float(s)
        return amt, cur
    except Exception:
        return None, cur


def parse_mileage(txt: Optional[str]):
    """Parse mileage strings and normalize to miles.

    Examples handled: '12,000 miles', '20k', '30,000 km', '18k km', '12-15k'
    Returns (value_in_miles:int|None, unit:str|None) where unit is 'mi'.
    """
    if not txt:
        return None, None
    s = str(txt).strip().lower()

    # detect unit in text
    is_km = bool(re.search(r'\bkm\b|kilomet', s))
    # handle ranges like '12-15k' or '12k-15k'
    m_range = re.search(r'([0-9,.kK]+)\s*[-–—]\s*([0-9,.kK]+)', s)
    if m_range:
        left = m_range.group(1)
        right = m_range.group(2)
        # prefer lower bound; if range uses 'k' on right (e.g. '12-15k'),
        # interpret both as thousands and apply multiplier to left
        if 'k' in right.lower() and 'k' not in left.lower():
            left = left + 'k'
        s_val = left
    else:
        # try to find first numeric token
        m = re.search(r'([0-9,.]+)\s*(k)?', s)
        if not m:
            return None, None
        s_val = m.group(1)
        k_marker = m.group(2)

    # handle 'k' shorthand
    # decide whether 'k' applies: either the extracted s_val contains k
    # (range-handled) or the original string had a 'k' marker
    has_k = 'k' in s_val.lower() or (m_range is None and 'k' in s.lower())
    if has_k:
        # extract the numeric part and multiply
        m2 = re.search(r'([0-9,.]+)\s*k', s_val + 'k', re.I)
        if m2:
            try:
                base = float(m2.group(1).replace(',', '')) * 1000
            except Exception:
                base = None
        else:
            base = None
    else:
        try:
            base = float(s_val.replace(',', ''))
        except Exception:
            base = None

    if base is None:
        return None, None

    # if parsed value looks like thousands (e.g., 12 -> 12), but we saw k marker absent,
    # we keep as-is. If value < 200 and no 'k' but context contains comma, it's thousands already.
    # Convert km to miles when detected
    value = int(round(base))
    if is_km:
        value = int(round(value * 0.621371))

    return value, 'mi'


def parse_year(txt: Optional[str]):
    """Extract a plausible 4-digit year (1900-2030) from `txt`.

    Returns int year or None.
    """
    if not txt:
        return None
    s = str(txt)
    # look for 4-digit year first
    m = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    if m:
        try:
            y = int(m.group(0))
            # sanity check
            if 1900 <= y <= 2030:
                return y
        except Exception:
            pass

    # fallback: 2-digit year -> map to 2000-2099 when <=30 else 1900s
    m2 = re.search(r"\b(\d{2})\b", s)
    if m2:
        try:
            yy = int(m2.group(1))
            if yy <= 30:
                return 2000 + yy
            else:
                return 1900 + yy
        except Exception:
            return None
    return None


def normalize_brand(txt: Optional[str]):
    """Simple brand normalizer: title-case and common alias mapping."""
    if not txt:
        return None
    s = str(txt).strip()
    mapping = {
        'vw': 'Volkswagen',
        'mini': 'MINI',
    }
    key = s.lower()
    if key in mapping:
        return mapping[key]
    # If the input already contains mixed/camel case (e.g. 'SampleBrand'),
    # preserve it rather than forcing title-case to avoid incorrect lowercasing.
    if any(c.isupper() for c in s[1:]):
        return s
    return s.title()


def finalize_detail_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a detail template output contains the canonical keys.

    Canonical keys: brand, model, year, price_value, price_raw, currency,
    mileage_value, mileage_unit, fuel, transmission, description, raw

    This function will not remove existing keys; it will add missing
    canonical keys (set to None when unavailable) and normalize common
    aliases (e.g., '_raw' -> 'raw', numeric/string price handling).
    """
    out = dict(data or {})
    # raw field: prefer explicit 'raw', then common underscored variants
    raw = out.get('raw') or out.get('_raw') or out.get('_raw_jsonld') or out.get('_raw_vehicle') or out.get('specs')
    out['raw'] = raw if raw is not None else None

    # description
    out['description'] = out.get('description') or out.get('desc') or None

    # model and brand (brand may be normalized already)
    out['brand'] = out.get('brand') or None
    out['model'] = out.get('model') or None

    # year: accept existing numeric or try parse from name/title
    year = out.get('year')
    if not year:
        name = out.get('name') or out.get('title')
        y = parse_year(name)
        out['year'] = y
    else:
        out['year'] = year

    # price handling: prefer explicit price_value, else try numeric 'price', else parse price_raw
    price_value = out.get('price_value')
    price_raw = out.get('price_raw') or out.get('price')
    if price_value is None:
        # if existing 'price' is numeric, use it
        p = out.get('price')
        if isinstance(p, (int, float)):
            price_value = float(p)
        else:
            # try parsing price_raw as string
            amt, cur = parse_price(price_raw)
            price_value = amt
            if not out.get('currency'):
                out['currency'] = cur
    out['price_value'] = price_value if price_value is not None else None
    out['price_raw'] = price_raw if price_raw is not None else None
    out['currency'] = out.get('currency') or None

    # mileage: prefer explicit normalized fields, else try parse from 'mileage' or specs
    m_val = out.get('mileage_value')
    m_unit = out.get('mileage_unit')
    if m_val is None:
        mtxt = out.get('mileage') or (out.get('specs') and out.get('specs').get('mileage')) if isinstance(out.get('specs'), dict) else out.get('mileage')
        if mtxt:
            mv, mu = parse_mileage(mtxt)
            m_val = mv
            m_unit = mu
    out['mileage_value'] = m_val if m_val is not None else None
    out['mileage_unit'] = m_unit if m_unit is not None else None

    # fuel and transmission
    out['fuel'] = out.get('fuel') or None
    out['transmission'] = out.get('transmission') or None

    return out
