"""Pagination by path segments, e.g., /used-cars/page/2

Extracts next page links where pages use path-based numbering.
"""
from __future__ import annotations

from typing import List, Dict, Any, Pattern
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate

_PAGE_PATH_RE: Pattern[str] = re.compile(r'/page/(\d+)', re.I)


class PaginationPathTemplate(CarTemplate):
    name = 'pagination_path'

    def get_next_page(self, html: str, page_url: str) -> str | None:
        soup = BeautifulSoup(html, 'lxml')

        # Prefer rel=next (handles values like "next" or "next prev")
        link = soup.find('a', attrs={'rel': re.compile(r'\bnext\b', re.I)})
        if link:
            href = link.get('href')
            if href:
                return urljoin(page_url, href)

        # Find hrefs containing /page/NUMBER — iterate hrefs directly
        for href in (a.get('href') for a in soup.find_all('a', href=True)):
            if href and _PAGE_PATH_RE.search(href):
                return urljoin(page_url, href)
        return None

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        raise NotImplementedError()

    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        raise NotImplementedError()
