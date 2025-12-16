"""Listing template that extracts listing URLs from embedded JSON or API payloads.

This template attempts to find JSON blobs in <script> tags (including
`window.__INITIAL_STATE__`, `application/json` blocks, or inline objects)
and traverses them to find URL-like strings under common keys such as
`url`, `href`, `link`, `permalink`.

It is intentionally conservative (does not make network requests) and
returns normalized absolute URLs discovered in the payloads.
"""
from typing import List, Any
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate

_SCRIPT_RE = re.compile(r'<script[^>]*>(.*?)</script>', re.I | re.S)


def _iter_json_strings(node: Any):
    """Yield candidate URL strings from nested JSON structures."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                yield k, v
            else:
                yield from _iter_json_strings(v)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, str):
                yield None, item
            else:
                yield from _iter_json_strings(item)


class ListingJSONAPITemplate(CarTemplate):
    name = 'listing_json_api'

    def _find_json_blocks(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'lxml')
        blocks = []
        # prefer explicit application/json scripts
        for tag in soup.find_all('script', attrs={'type': 'application/json'}):
            if tag.string:
                blocks.append(tag.string)

        # fallback: script tags that contain JSON-like content
        if not blocks:
            for raw in _SCRIPT_RE.findall(html):
                txt = raw.strip()
                # heuristics: starts with { or [ or contains window.__INITIAL_STATE__
                if txt.startswith('{') or txt.startswith('[') or 'INITIAL_STATE' in txt or 'window.__' in txt:
                    blocks.append(txt)
        return blocks

    def _parse_json_safely(self, txt: str):
        # try plain json
        try:
            return json.loads(txt)
        except Exception:
            # try to extract JSON snippet within assignment e.g. window.__STATE__ = {...};
            m = re.search(r'={1}\s*({[\s\S]+})', txt)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    return None
        return None

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        blocks = self._find_json_blocks(html)
        urls = []
        for b in blocks:
            data = self._parse_json_safely(b)
            if not data:
                continue
            for key, sval in _iter_json_strings(data):
                if not sval:
                    continue
                # quick filter: looks like a path or url
                if sval.startswith('/') or sval.startswith('http'):
                    # some strings are image urls etc; prefer those that look like listing links
                    if any(tok in sval.lower() for tok in ('/car', '/vehicle', '/listing', '/stock', '/used')) or key in ('url', 'href', 'link', 'permalink'):
                        urls.append(urljoin(page_url, sval))
                    else:
                        # also accept if string contains typical listing query params
                        if any(p in sval for p in ('?id=', '&id=', '/v/')):
                            urls.append(urljoin(page_url, sval))

        # dedupe while preserving order
        return list(dict.fromkeys(urls))

    def get_next_page(self, html: str, page_url: str):
        return None

    def parse_car_page(self, html: str, car_url: str):
        raise NotImplementedError()
