"""Hybrid template: prefer JSON-LD for core fields, fallback to HTML specs.

This template attempts to parse price/model/name from JSON-LD Vehicle
objects and supplements missing fields by scraping spec tables from HTML.
"""
from typing import Dict, Any
import json
import re
import html as _html
from bs4 import BeautifulSoup
from .base import CarTemplate
from .utils import parse_mileage, parse_year, normalize_brand

_SCRIPT_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def _extract_text(node: Any) -> Any:
    if node is None:
        return None
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        return node.get('name') or node.get('title') or None
    return str(node).strip()


class HybridJSONHTMLTemplate(CarTemplate):
    name = 'hybrid_json_html'

    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {'_source': 'hybrid', 'specs': {}}

        # Try JSON-LD first
        for raw in _SCRIPT_RE.findall(html):
            try:
                data = json.loads(_html.unescape(raw))
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                t = item.get('@type')
                if t and ('Vehicle' in str(t) or 'vehicle' in str(t).lower()):
                    out['name'] = _extract_text(item.get('name'))
                    out['brand'] = _extract_text(item.get('brand') or item.get('manufacturer'))
                    out['model'] = _extract_text(item.get('model') or item.get('vehicleModel'))
                    offers = item.get('offers') or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    out['price'] = _extract_text(offers.get('price') or item.get('price'))
                    out['currency'] = _extract_text(offers.get('priceCurrency'))
                    out['_raw_jsonld'] = item
                    break

        # Parse HTML specs to fill gaps
        soup = BeautifulSoup(html, 'lxml')
        # Find tables and simple key/value rows
        for table in soup.find_all('table'):
            for tr in table.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if not th or not td:
                    continue
                key = th.get_text(separator=' ').strip().lower()
                val = td.get_text(separator=' ').strip()
                nk = key.replace(' ', '_')
                out['specs'][nk] = val
                # common fields: mileage, fuel, transmission
                if 'mileage' in key and 'mileage' not in out:
                    out['mileage'] = val
                    # normalized mileage
                    m_val, m_unit = parse_mileage(val)
                    if m_val:
                        out['mileage_value'] = m_val
                        out['mileage_unit'] = m_unit
                if 'fuel' in key and 'fuel' not in out:
                    out['fuel'] = val
                if 'transmission' in key and 'transmission' not in out:
                    out['transmission'] = val

        # normalize brand/year if present in specs
        if out.get('specs'):
            if out['specs'].get('brand') and not out.get('brand'):
                out['brand'] = normalize_brand(out['specs'].get('brand'))
            if out['specs'].get('year'):
                y = parse_year(out['specs'].get('year'))
                if y:
                    out['year'] = y

        return out
