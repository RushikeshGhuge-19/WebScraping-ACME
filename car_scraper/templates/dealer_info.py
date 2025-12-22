"""Dealer/site-level info extractor.

Parses JSON-LD for Organization / AutomotiveBusiness to extract site
level metadata such as name, address, phone and email.
"""
from typing import Dict, Any
import json
import logging
import re
import html as _html
from bs4 import BeautifulSoup
from .base import CarTemplate

_SCRIPT_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def _get_text(node: Any) -> Any:
    if node is None:
        return None
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        return node.get('name') or node.get('telephone') or node.get('email')
    return str(node)


class DealerInfoTemplate(CarTemplate):
    # Use the canonical detection name expected by the engine
    name = 'dealer_info_jsonld'

    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        # This template expects a site-level page (could be any page)
        soup = BeautifulSoup(html, 'lxml')
        # search JSON-LD for Organization or AutomotiveBusiness
        for raw in _SCRIPT_RE.findall(str(soup)):
            try:
                data = json.loads(_html.unescape(raw))
            except json.JSONDecodeError as exc:
                logging.getLogger(__name__).debug("Skipping invalid JSON-LD blob: %s", exc)
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                t = item.get('@type') or ''
                if 'Organization' in str(t) or 'AutomotiveBusiness' in str(t):
                    out: Dict[str, Any] = {}
                    out['name'] = _get_text(item.get('name'))
                    out['telephone'] = _get_text(item.get('telephone') or item.get('phone'))
                    out['email'] = _get_text(item.get('email'))
                    address = item.get('address') or {}
                    if isinstance(address, dict):
                        out['address'] = ', '.join(filter(None, [
                            address.get('streetAddress'),
                            address.get('addressLocality'),
                            address.get('addressRegion'),
                            address.get('postalCode'),
                            address.get('addressCountry'),
                        ]))
                    out['_raw'] = item
                    return out

        # Fallback: look for common page-level contact selectors
        out = {'name': None, 'telephone': None, 'email': None}
        # Dragon2000 inline JS fallback: parse var d2k = { dealerDetails: { Email: "..." } }
        # Only use this if JSON-LD did not provide an email
        js_match = re.search(r"var\s+d2k\s*=\s*({[\s\S]+?})\s*;", str(soup), re.I)
        if js_match and not out.get('email'):
            js_blob = js_match.group(1)
            # try to find dealerDetails.Email with a tolerant regex
            m = re.search(r"dealerDetails\s*:\s*{[\s\S]*?Email\s*:\s*['\"]([^'\"]+)['\"]", js_blob, re.I)
            if m:
                out['email'] = m.group(1).strip()
        tel = soup.select_one('a[href^="tel:"]')
        if tel:
            out['telephone'] = tel.get_text(strip=True)
        mail = soup.select_one('a[href^="mailto:"]')
        if mail:
            out['email'] = mail.get_text(strip=True)
        h1 = soup.find('h1')
        if h1:
            out['name'] = h1.get_text(strip=True)
        return out
