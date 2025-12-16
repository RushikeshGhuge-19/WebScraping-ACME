"""Template to detect AJAX / infinite-scroll listing endpoints and extract URLs.

This template inspects the page for common load-more patterns and XHR
endpoints embedded in inline scripts (e.g., fetch/axios URLs, data-load
attributes). It returns candidate listing URLs discovered in the page.
"""
from typing import List
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate

_FETCH_RE = re.compile(r"fetch\(['\"](.*?)['\"]")
_AXIOS_RE = re.compile(r"axios\.(get|post)\(['\"](.*?)['\"]")
_XHR_URL_RE = re.compile(r"['\"](\/[^'\"]+?(?:listing|list|search|load|api|ajax)[^'\"]*)['\"]", re.I)


class ListingAjaxInfiniteTemplate(CarTemplate):
    name = 'listing_ajax_infinite'

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        # 1) Look for container with data-load-url or data-next
        for el in soup.find_all(attrs={}) :
            # scanning attributes cheaply
            attrs = getattr(el, 'attrs', {})
            for a_k, a_v in attrs.items():
                if isinstance(a_v, str) and any(tok in a_k.lower() for tok in ('data-load', 'data-next', 'data-url')):
                    if a_v:
                        urls.append(urljoin(page_url, a_v))

        # 2) Find fetch/axios endpoints in scripts
        for m in _FETCH_RE.findall(html):
            urls.append(urljoin(page_url, m))
        for _g, m in _AXIOS_RE.findall(html):
            urls.append(urljoin(page_url, m))

        # 3) Heuristic XHR url matches inside scripts
        for m in _XHR_URL_RE.findall(html):
            urls.append(urljoin(page_url, m))

        # 4) fallback: find load-more anchor links
        for a in soup.find_all('a', href=True):
            if any(tok in (a.get_text(' ') or '').lower() for tok in ('load', 'more', 'show more')) or any(tok in a['href'].lower() for tok in ('page=', '/page/', 'offset=')):
                urls.append(urljoin(page_url, a['href']))

        # dedupe and return
        return list(dict.fromkeys(urls))

    def get_next_page(self, html: str, page_url: str):
        # prefer first discovered candidate
        found = self.get_listing_urls(html, page_url)
        return found[0] if found else None

    def parse_car_page(self, html: str, car_url: str):
        raise NotImplementedError()
