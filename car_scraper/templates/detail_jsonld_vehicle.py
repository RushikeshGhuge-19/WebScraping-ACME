"""Canonical file `detail_jsonld_vehicle.py` — delegates to existing jsonld implementation.

This wrapper preserves the authoritative filename while reusing the
previous `JSONLDVehicleTemplate` implementation to avoid duplication.
"""
from typing import Dict, Any
from .jsonld_vehicle import JSONLDVehicleTemplate
from .utils import extract_microdata, make_soup, extract_meta_values


class DetailJSONLDVehicle(JSONLDVehicleTemplate):
    name = 'detail_jsonld_vehicle'

    # inherits parse_car_page from JSONLDVehicleTemplate
    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        out = super().parse_car_page(html, car_url)
        # If JSON-LD returned nothing useful, try microdata/meta fallbacks
        useful = bool(out.get('name') or out.get('brand') or out.get('price'))
        if not useful:
            # try microdata
            micro_list = extract_microdata(html)
            if micro_list:
                # prefer first reasonably populated microdata object
                for micro in micro_list:
                    if micro.get('price') or micro.get('name'):
                        micro['_source'] = 'microdata-fallback'
                        micro['confidence'] = 0.5
                        out.update(micro)
                        return out

            # meta fallback
            soup = make_soup(html)
            meta = extract_meta_values(soup)
            if meta and (meta.get('price') or meta.get('title')):
                meta['_source'] = 'meta-fallback'
                meta['confidence'] = 0.3
                out.update(meta)
                return out

        return out
