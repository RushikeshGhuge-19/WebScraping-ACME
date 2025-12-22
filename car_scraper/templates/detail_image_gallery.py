"""Detail template to extract image galleries and video sources from vehicle pages.

Collects images from JSON-LD, Open Graph, gallery/carousel DOMs, and
`img` elements with `data-src`/`data-large` fallbacks. Returns a dict
with `images` and `videos` lists.
"""
from typing import Dict, Any, List
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate

_SCRIPT_JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


class DetailImageGallery(CarTemplate):
    name = 'detail_image_gallery'

    def _collect_from_jsonld(self, html: str, base: str) -> List[str]:
        out: List[str] = []
        for raw in _SCRIPT_JSONLD_RE.findall(html):
            try:
                data = json.loads(raw)
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                img = item.get('image') or item.get('images')
                if isinstance(img, str):
                    out.append(urljoin(base, img))
                elif isinstance(img, list):
                    for i in img:
                        if isinstance(i, str):
                            out.append(urljoin(base, i))
        return out

    def _collect_from_dom(self, soup: BeautifulSoup, base: str) -> List[str]:
        out: List[str] = []
        # common gallery selectors
        for sel in ('.gallery', '.carousel', '.thumbnails', '.slider', 'ul.gallery'):
            for container in soup.select(sel):
                for img in container.find_all('img'):
                    src = img.get('data-large') or img.get('data-src') or img.get('src') or img.get('data-original')
                    if src:
                        out.append(urljoin(base, src))

        # Dragon2000 specific selectors: side-thumbs carousel and container links
        for a in soup.select('div.vehicle-content-slider--side-thumbs__carousel a[href], div.vehicle-content-slider-container a[href]'):
            href = a.get('href')
            if href:
                out.append(urljoin(base, href))

        for img in soup.select('div.vehicle-content-slider--side-thumbs__thumbs-prev img[data-src]'):
            src = img.get('data-src')
            if src:
                out.append(urljoin(base, src))

        # fallback: any img with zoom/large hints
        for img in soup.find_all('img'):
            src = img.get('data-large') or img.get('data-src') or img.get('src')
            if not src:
                continue
            # prefer larger images (heuristic: filenames containing large, full, zoom)
            if any(t in src.lower() for t in ('large', 'full', 'zoom', '1024', '800')):
                out.append(urljoin(base, src))

        # OG image
        og = soup.find('meta', attrs={'property': 'og:image'})
        if og and og.get('content'):
            out.append(urljoin(base, og['content']))

        return out

    def _collect_videos(self, soup: BeautifulSoup, base: str) -> List[str]:
        vids: List[str] = []
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                vids.append(urljoin(base, src))
            for src_tag in video.find_all('source'):
                s = src_tag.get('src')
                if s:
                    vids.append(urljoin(base, s))
        return vids

    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'lxml')
        images: List[str] = []

        images.extend(self._collect_from_jsonld(html, car_url))
        images.extend(self._collect_from_dom(soup, car_url))
        # dedupe while preserving order
        images = list(dict.fromkeys([i for i in images if i]))

        videos = self._collect_videos(soup, car_url)
        videos = list(dict.fromkeys(videos))

        return {'_source': 'image-gallery', 'images': images, 'videos': videos}
