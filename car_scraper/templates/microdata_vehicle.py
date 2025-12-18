"""SUPPORTING MODULE — Microdata parsing strategy (NOT a structural template).

This module implements a microdata parsing strategy used as a fallback
by DETAIL templates. It is intentionally a helper and MUST NOT be
registered as a structural template. Structural templates should invoke
these helpers where appropriate.
"""
from typing import Dict, Any, Optional
import logging
from .base import CarTemplate
from .utils import make_soup, parse_price, parse_mileage, parse_year, normalize_brand


def _extract_text(node: Optional[Any]) -> Optional[str]:
    if node is None:
        return None
    if getattr(node, 'get', None) and node.get('content'):
        return node.get('content')
    try:
        return node.get_text(strip=True)
    except Exception as exc:
        # Log parsing errors for diagnosis but fall back to a safe string
        try:
            logging.getLogger(__name__).debug("_extract_text fallback: %s", exc, exc_info=True)
        except Exception:
            # Ensure logging failures do not propagate
            pass
        return str(node).strip()

class MicrodataVehicleTemplate(CarTemplate):
    name = 'microdata_vehicle'

    def parse_car_page(self, html: str, car_url: str) -> Dict:
        soup = make_soup(html)
        # find the first itemscope that looks like a vehicle
        tag = None
        for t in soup.find_all(attrs={"itemscope": True}):
            itype = (t.get('itemtype') or '').lower()
            if 'vehicle' in itype:
                tag = t
                break

        if not tag:
            return {
                '_source': 'microdata',
                '_raw': None,
                'confidence': 0.0,
                'name': None,
                'brand': None,
                'model': None,
                'description': None,
                'price_raw': None,
                'price': None,
                'currency': None,
                'mileage': None,
                'mileage_unit': None,
                'year': None,
            }
        out: Dict[str, Any] = {}
        out['name'] = _extract_text(tag.find(attrs={'itemprop': 'name'}))
        brand_raw = _extract_text(tag.find(attrs={'itemprop': 'brand'}))
        out['brand'] = normalize_brand(brand_raw)
        out['model'] = _extract_text(tag.find(attrs={'itemprop': 'model'}))
        out['description'] = _extract_text(tag.find(attrs={'itemprop': 'description'}))

        # price
        price_node = tag.find(attrs={'itemprop': 'price'}) or tag.find('meta', attrs={'itemprop': 'price'})
        price_raw = _extract_text(price_node)
        amt, cur = parse_price(price_raw)
        out['price_raw'] = price_raw
        out['price'] = amt
        out['currency'] = cur

        # mileage: common microdata props
        mileage_node = tag.find(attrs={'itemprop': 'mileageFromOdometer'}) or tag.find(attrs={'itemprop': 'mileage'})
        mileage_txt = _extract_text(mileage_node)
        mval, munit = parse_mileage(mileage_txt)
        out['mileage'] = mval
        out['mileage_unit'] = munit

        # year
        year_node = tag.find(attrs={'itemprop': 'vehicleModelYear'}) or tag.find(attrs={'itemprop': 'year'})
        year_txt = _extract_text(year_node)
        out['year'] = parse_year(year_txt)

        out['_raw'] = {k: v for k, v in tag.attrs.items()}
        out['_source'] = 'microdata'

        # confidence: proportion of core fields present
        core = sum(1 for k in ('brand', 'model', 'price') if out.get(k))
        out['confidence'] = round(core / 3.0, 2)
        return out
