"""SUPPORTING MODULE — JSON API listing transport mechanism (NOT a structural template).

This module implements a transport/parsing strategy to extract listing
URLs from embedded JSON blobs or inline JSON used by SPAs. It should be
invoked from structural LISTING templates when necessary, not treated
as an independent structural template.
"""
from typing import List, Dict, Any, Optional
import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import CarTemplate
from .utils import make_soup

# Whitelist of path segments that indicate listing/vehicle URLs
LISTING_PATH_SEGMENTS = {'car', 'cars', 'listing', 'listings', 'vehicle', 'vehicles', 'stock', 'used'}
# Maximum number of leading path segments to inspect for a listing indicator
MAX_CHECK_SEGMENTS = 3
# Allowed domains for absolute URLs. Only absolute URLs whose netloc is in
# this list will be considered for path-based listing detection. Keep
# conservative by default (example.com included for tests).
ALLOWED_DOMAINS = {'example.com'}
# Plausible resource token: numeric id or slug-like string (lowercase letters,
# numbers and hyphens, length >= 3)
SLUG_RE = re.compile(r'^[a-z0-9-]{3,}$')


class JSONAPIListingTemplate(CarTemplate):
    name = 'json_api_listing'

    def _extract_json_blobs(self, html: str) -> List[Dict[str, Any]]:
        soup = make_soup(html)
        out: List[Dict[str, Any]] = []
        # common: <script type="application/json">...</script>
        for tag in soup.find_all('script', type=lambda t: t and 'json' in t):
            raw = tag.string or ''
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if isinstance(data, dict):
                out.append(data)

        # also try application/ld+json (some sites put arrays/objects with listings)
        for tag in soup.find_all('script', type='application/ld+json'):
            raw = tag.string or ''
            try:
                data = json.loads(raw)
            except Exception:
                # try to extract JSON object inside assignment
                m = re.search(r'={1}\s*({[\s\S]+})', raw)
                if not m:
                    continue
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    continue
            if isinstance(data, dict):
                out.append(data)

        return out

    def _is_listing_url(self, url_str: str) -> bool:
        """Check if a URL string appears to be a listing or vehicle URL.
        
        Parses the URL and checks if the path contains a whitelisted segment
        (e.g., "car", "listing", "vehicle") as a whole path component
        (case-insensitive).
        """
        try:
            parsed = urlparse(url_str)
            path = (parsed.path or '').lower()
            # If absolute URL, require allowlist on domain
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                domain = parsed.netloc.split(':', 1)[0].lower()
                if domain not in ALLOWED_DOMAINS:
                    return False

            # Split path on "/" and consider only the leading components
            segments = [s for s in path.split('/') if s]
            if not segments:
                return False

            # Only inspect the first N segments to avoid false positives
            inspect_segments = segments[:MAX_CHECK_SEGMENTS]

            for idx, seg in enumerate(inspect_segments):
                if seg in LISTING_PATH_SEGMENTS:
                    # require a following plausible resource token (e.g., id or slug)
                    # e.g. /cars/123 or /vehicle/ford-fiesta
                    if idx + 1 < len(segments):
                        token = segments[idx + 1]
                        if token.isdigit() or SLUG_RE.match(token):
                            return True
                    # if there is no following token within inspected range, reject
                    return False
            return False
        except Exception:
            return False

    def _find_urls_in_obj(self, obj: Any) -> List[str]:
        urls: List[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    # Check if string looks like a URL (protocol-relative, absolute, or path-absolute)
                    if v.startswith(('http://', 'https://', '//', '/')):
                        if self._is_listing_url(v):
                            urls.append(v)
                else:
                    # Recursively search non-string values
                    urls.extend(self._find_urls_in_obj(v))
        elif isinstance(obj, list):
            for it in obj:
                urls.extend(self._find_urls_in_obj(it))
        return urls

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        blobs = self._extract_json_blobs(html)
        urls: List[str] = []
        for b in blobs:
            raw_urls = self._find_urls_in_obj(b)
            # Resolve relative URLs to absolute using page_url
            urls.extend([urljoin(page_url, u) for u in raw_urls])

        # de-duplicate while preserving order
        return list(dict.fromkeys(urls))

    def get_next_page(self, html: str, page_url: str) -> Optional[str]:
        # try to extract a `next` or `page` URL from JSON blobs
        blobs = self._extract_json_blobs(html)
        for b in blobs:
            if isinstance(b, dict):
                for key in ('next', 'nextPage', 'next_page', 'pagination'):
                    if key in b and isinstance(b[key], str):
                        return urljoin(page_url, b[key])
                # nested pagination
                pag = b.get('pagination') or b.get('meta') or b.get('page')
                if isinstance(pag, dict):
                    next_url = pag.get('next')
                    if isinstance(next_url, str):
                        return urljoin(page_url, next_url)
        return None

    def parse_car_page(self, html: str, car_url: str):
        raise NotImplementedError()
