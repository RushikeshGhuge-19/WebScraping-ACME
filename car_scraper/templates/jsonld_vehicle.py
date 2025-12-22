"""Template to parse JSON-LD Vehicle schema from saved HTML.

This implementation uses shared utilities for JSON-LD extraction and
returns a small confidence score and provenance information.
"""
from typing import Dict, Any, Optional
from .base import CarTemplate
from .utils import extract_jsonld_objects
from ..utils.schema_normalizer import parse_price, parse_year


def _extract_text(node: Any) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        return _extract_text(node.get('name') or node.get('@value'))
    return str(node).strip()


def _is_vehicle(node: Any) -> bool:
    # Accept both Vehicle and Car types; handle lists and IRIs
    t = node.get('@type') if isinstance(node, dict) else None
    if not t:
        return False
    if isinstance(t, list):
        types = [str(x).lower() for x in t if isinstance(x, (str,))]
    else:
        types = [str(t).lower()]
    # check for common local type names such as vehicle or car
    for x in types:
        # split IRIs to local name
        local = x.split('/')[-1].split('#')[-1]
        if local in ('vehicle', 'car', 'automobile'):
            return True
    return False


class JSONLDVehicleTemplate(CarTemplate):
    name = 'jsonld_vehicle'

    def parse_car_page(self, html: str, car_url: str) -> Dict:
        objs = extract_jsonld_objects(html)
        for item in objs:
            # If this script tag is a top-level graph, iterate inner nodes
            items = []
            if isinstance(item, dict) and '@graph' in item and isinstance(item['@graph'], list):
                items = item['@graph']
            else:
                items = [item]

            for node in items:
                if not isinstance(node, dict):
                    continue
                if _is_vehicle(node):
                    out: Dict[str, Any] = {}
                    brand = node.get('brand') or node.get('manufacturer') or node.get('make')
                    out['brand'] = _extract_text(brand)
                    out['model'] = _extract_text(node.get('model') or node.get('vehicleModel'))
                    offers = node.get('offers') or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    out['price'] = _extract_text(offers.get('price') or node.get('price'))
                    raw_price = _extract_text(offers.get('price') or node.get('price'))
                    amt, cur = parse_price(raw_price)
                    out['price_raw'] = raw_price
                    out['price'] = amt
                    out['currency'] = cur or _extract_text(offers.get('priceCurrency'))
                    out['name'] = _extract_text(node.get('name'))
                    out['description'] = _extract_text(node.get('description'))
                    out['_raw'] = node
                    out['_source'] = 'json-ld'
                    # try to extract year from name or explicit fields
                    name_val = out.get('name')
                    y = parse_year(name_val)
                    if y:
                        out['year'] = y
                    
                    # Confidence: proportion of core fields with meaningful values
                    core = 0
                    for k in ('brand', 'model'):
                        val = out.get(k)
                        if val and (not isinstance(val, str) or len(val.strip()) > 0):
                            core += 1
                    # For price: accept non-None numeric values (including 0 if amt parsed successfully)
                    price_val = out.get('price')
                    if price_val is not None and isinstance(price_val, (int, float)) and price_val >= 0:
                        core += 1
                    out['confidence'] = round(core / 3.0, 2)
                    return out

        return {'_source': 'json-ld', '_raw': {}, 'confidence': 0.0}