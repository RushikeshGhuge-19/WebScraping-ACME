"""Template to parse JSON-LD Vehicle schema from saved HTML.

This implementation uses shared utilities for JSON-LD extraction and
returns a small confidence score and provenance information.
"""
from typing import Dict, Any, Optional
from .base import CarTemplate
from .utils import extract_jsonld_objects, parse_price


def _extract_text(node: Any) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        return _extract_text(node.get('name') or node.get('@value'))
    return str(node).strip()


def _is_vehicle(node: Any) -> bool:
    t = node.get('@type') if isinstance(node, dict) else None
    if not t:
        return False
    if isinstance(t, list):
        types = [str(x).lower() for x in t]
    else:
        types = [str(t).lower()]
    return any('vehicle' in x for x in types)


class JSONLDVehicleTemplate(CarTemplate):
    name = 'jsonld_vehicle'

    def parse_car_page(self, html: str, car_url: str) -> Dict:
        objs = extract_jsonld_objects(html)
        for item in objs:
            if not isinstance(item, dict):
                continue
            if _is_vehicle(item):
                out: Dict[str, Any] = {}
                brand = item.get('brand') or item.get('manufacturer') or item.get('make')
                out['brand'] = _extract_text(brand)
                out['model'] = _extract_text(item.get('model') or item.get('vehicleModel'))
                offers = item.get('offers') or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                out['price'] = _extract_text(offers.get('price') or item.get('price'))
                raw_price = _extract_text(offers.get('price') or item.get('price'))
                amt, cur = parse_price(raw_price)
                out['price_raw'] = raw_price
                out['price'] = amt
                out['currency'] = cur or _extract_text(offers.get('priceCurrency'))
                out['name'] = _extract_text(item.get('name'))
                out['description'] = _extract_text(item.get('description'))
                out['_raw'] = item
                out['_source'] = 'json-ld'
                # Simple confidence: proportion of core fields present
                core = sum(1 for k in ('brand', 'model', 'price') if out.get(k))
                out['confidence'] = round(core / 3.0, 2)
                return out

        return {'_source': 'json-ld', '_raw': None, 'confidence': 0.0}
