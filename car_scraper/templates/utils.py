"""Shared parsing utilities for templates.

Provides a minimal set of helpers for JSON-LD extraction, microdata
and meta tag fallbacks, and a single `make_soup` helper so pages are
parsed consistently.
"""
from typing import List, Dict, Any, Optional
import json
import html as _html
import re
import warnings
from bs4 import BeautifulSoup

# Pre-compiled regex patterns for performance (avoid recompilation)
_RE_YEAR = re.compile(r'\b(19\d{2}|20\d{2})\b')
_RE_YEAR_2DIGIT = re.compile(r'\b(\d{2})\b')
_RE_VERSION = re.compile(r'^(\d+)')
_RE_JSON_ASSIGN = re.compile(r'={1}\s*({[\s\S]+})')
_RE_CURRENCY_CODE = re.compile(r'\b(GBP|USD|EUR|AUD|CAD|JPY|CHF)\b', re.I)
_RE_PRICE_SYMBOLS = re.compile(r'[A-Za-z£$€¥,\s]+')
_RE_PRICE_CLEAN = re.compile(r'[^0-9\.\-]')
_RE_KM_UNIT = re.compile(r'\bkm\b|kilomet')
_RE_MILEAGE_RANGE = re.compile(r'([0-9,.kK]+)\s*[-–—]\s*([0-9,.kK]+)')
_RE_MILEAGE_NUMERIC = re.compile(r'([0-9,.]+)\s*(k)?')
_RE_MILEAGE_K = re.compile(r'([0-9,.]+)\s*k', re.I)

try:
    from packaging.version import parse as parse_version
except ImportError:
    # Fallback: simple version tuple parsing if packaging not available
    def parse_version(version_str: str):
        """Parse version string into comparable tuple."""
        try:
            parts = []
            for part in version_str.split('.'):
                # Extract leading digits, ignore non-numeric suffixes
                match = _RE_VERSION.match(part)
                if match:
                    parts.append(int(match.group(1)))
            return tuple(parts) if parts else (0,)
        except Exception:
            return (0,)


def make_soup(html: str) -> BeautifulSoup:
    """Parse HTML using BeautifulSoup with lxml backend.
    
    Suppresses known DeprecationWarning from lxml HTMLParser regarding
    'strip_cdata' option in BeautifulSoup 4.12+ with lxml 4.9+.
    """
    # Only suppress for known problematic version combinations
    # Check if we're running BS4 4.12+ that emits the warning
    bs_version = getattr(BeautifulSoup, '__version__', None)
    suppress_warning = False
    if bs_version:
        try:
            suppress_warning = parse_version(bs_version) >= parse_version('4.12')
        except Exception:
            suppress_warning = False
    
    if suppress_warning:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=DeprecationWarning,
                message=r".*The 'strip_cdata' option of HTMLParser.*",
                module=r".*_lxml.*",
            )
            return BeautifulSoup(html, 'lxml')
    else:
        return BeautifulSoup(html, 'lxml')


def extract_jsonld_objects(html: Optional[str] = None, soup: Optional[BeautifulSoup] = None) -> List[Dict[str, Any]]:
    if soup is None:
        if not html:
            return []
        soup = make_soup(html)
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all('script', type='application/ld+json'):
        raw = tag.string or ''
        # try simple json loads first
        try:
            data = json.loads(_html.unescape(raw))
        except (json.JSONDecodeError, ValueError):
            # try to extract a JSON object from an assignment (window.__STATE__ = {...})
            m = _RE_JSON_ASSIGN.search(raw)
            if m:
                try:
                    data = json.loads(m.group(1))
                except (json.JSONDecodeError, ValueError):
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


def extract_microdata(html: Optional[str] = None, soup: Optional[BeautifulSoup] = None) -> List[Dict[str, Any]]:
    if soup is None:
        if not html:
            return []
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
    # Delegate to canonical normalizer to avoid duplication
    from ..utils.schema_normalizer import parse_price as _schema_parse_price

    return _schema_parse_price(txt)


def parse_mileage(txt: Optional[str]):
    """Parse mileage strings and normalize to miles.

    Examples handled: '12,000 miles', '20k', '30,000 km', '18k km', '12-15k'
    Returns (value_in_miles:int|None, unit:str|None) where unit is 'mi'.
    """
    from ..utils.schema_normalizer import parse_mileage as _schema_parse_mileage

    return _schema_parse_mileage(txt)


def parse_year(txt: Optional[str]):
    """Extract a plausible 4-digit year (1900-2030) from `txt`.

    Returns int year or None.
    """
    from ..utils.schema_normalizer import parse_year as _schema_parse_year

    return _schema_parse_year(txt)


def normalize_brand(txt: Optional[str]):
    """Simple brand normalizer: title-case and common alias mapping."""
    from ..utils.schema_normalizer import normalize_brand as _schema_normalize_brand

    return _schema_normalize_brand(txt)


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
