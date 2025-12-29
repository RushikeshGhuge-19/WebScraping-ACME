from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional


# Pre-compiled regex for performance
_PRICE_RE = re.compile(r'[-€£$\u00A3,\s]+')
_MILEAGE_RE = re.compile(r'[,\s]+')
_MILEAGE_UNIT_RE = re.compile(r'\b(miles|mile|mi)\b', re.I)
_YEAR_RE = re.compile(r'(19\d{2}|20\d{2})')
_BRAND_CLEAN_RE = re.compile(r'[^a-z0-9]')
_CURRENCY_RE = re.compile(r'\b(GBP|USD|EUR|AUD|CAD|JPY|CHF)\b', re.I)
_KM_RE = re.compile(r'\bkm\b|kilomet', re.I)
_MILEAGE_RANGE = re.compile(r'([0-9,.kK]+)\s*[-–—]\s*([0-9,.kK]+)')
_MILEAGE_NUMERIC = re.compile(r'([0-9,.]+)\s*(k)?', re.I)

# Cache current year to avoid repeated datetime calls
_CURRENT_YEAR = datetime.now().year


class SchemaNormalizer:
    """Normalize common vehicle fields into canonical types.

    Methods are intentionally conservative: they return None when a value
    cannot be confidently normalized.
    """

    BRAND_MAP = {
        'vw': 'Volkswagen',
        'volkswagen': 'Volkswagen',
        'mini': 'MINI',
        'bmw': 'BMW',
        'ford': 'Ford',
        'toyota': 'Toyota',
    }

    @classmethod
    def normalize_price(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).strip()
        if not s:
            return None
        cleaned = _PRICE_RE.sub('', s)
        if not cleaned:
            return None
        try:
            return int(float(cleaned)) if '.' in cleaned else int(cleaned)
        except (ValueError, OverflowError):
            return None

    @classmethod
    def normalize_mileage(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).strip().lower()
        if not s:
            return None

        # detect km vs miles
        is_km = bool(_KM_RE.search(s))

        # handle ranges like '12-15k' or '12k-15k'
        m_range = _MILEAGE_RANGE.search(s)
        if m_range:
            left = m_range.group(1)
            right = m_range.group(2)
            if 'k' in right.lower() and 'k' not in left.lower():
                left = left + 'k'
            s_val = left
            k_marker = None
        else:
            # remove separators for numeric parsing
            cleaned = _MILEAGE_RE.sub('', s)
            m = _MILEAGE_NUMERIC.search(cleaned)
            if not m:
                return None
            s_val = m.group(1)
            k_marker = m.group(2)

        # handle 'k' shorthand
        has_k = 'k' in s_val.lower() or ('k' in (k_marker or '').lower())        
        try:
            if has_k:
                num = float(s_val.replace(',', '').replace('k', '')) * 1000
            else:
                num = float(s_val.replace(',', ''))
        except (ValueError, AttributeError):
            return None

        value_int = int(round(num))
        if is_km:
            value_int = int(round(value_int * 0.621371))
        return value_int

    @classmethod
    def normalize_year(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            year = value
        else:
            s = str(value).strip()
            if not s:
                return None
            m = _YEAR_RE.search(s)
            if m:
                year = int(m.group(1))
            else:
                # fallback: 2-digit year -> map to 2000-2099 when <=30 else 1900s
                m2 = re.search(r"\b(\d{2})\b", s)
                if not m2:
                    return None
                yy = int(m2.group(1))
                year = 2000 + yy if yy <= 30 else 1900 + yy
        if 1900 <= year <= _CURRENT_YEAR + 1:
            return year
        return None

    @classmethod
    def normalize_brand(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        key = _BRAND_CLEAN_RE.sub('', s.lower())
        mapped = cls.BRAND_MAP.get(key)
        if mapped:
            return mapped
        # preserve existing mixed/camel case in brand names
        if any(c.isupper() for c in s[1:]):
            return s
        return s.title()

    @classmethod
    def normalize(cls, record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Normalize fields on a record and return (normalized, issues)."""
        issues: List[str] = []
        out = dict(record)

        for field, normalizer in (
            ('price', cls.normalize_price),
            ('mileage', cls.normalize_mileage),
            ('year', cls.normalize_year),
            ('brand', cls.normalize_brand),
        ):
            original = record.get(field)
            normalized = normalizer(original)
            if normalized is None and original is not None:
                issues.append(f'{field}:unparsed')
            out[field] = normalized

        return out, issues


# Convenience wrapper functions for backward compatibility

def parse_price(txt: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """Parse price string -> (amount, currency). Deprecated: use SchemaNormalizer."""
    if not txt:
        return None, None
    amt = SchemaNormalizer.normalize_price(txt)
    cur = None
    if isinstance(txt, str):
        m = _CURRENCY_RE.search(txt)
        if m:
            cur = m.group(1).upper()
        elif txt.startswith('£'):
            cur = 'GBP'
        elif txt.startswith('$'):
            cur = 'USD'
        elif txt.startswith('€'):
            cur = 'EUR'
    return amt, cur


def parse_mileage(txt: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """Parse mileage string -> (value, unit). Deprecated: use SchemaNormalizer."""
    val = SchemaNormalizer.normalize_mileage(txt)
    return (val, 'mi') if val is not None else (None, None)


def parse_year(txt: Optional[str]) -> Optional[int]:
    """Extract year from text. Deprecated: use SchemaNormalizer."""
    return SchemaNormalizer.normalize_year(txt)


def normalize_brand(txt: Optional[str]) -> Optional[str]:
    """Normalize brand name. Deprecated: use SchemaNormalizer."""
    return SchemaNormalizer.normalize_brand(txt)


__all__ = ['SchemaNormalizer', 'parse_price', 'parse_mileage', 'parse_year', 'normalize_brand']
