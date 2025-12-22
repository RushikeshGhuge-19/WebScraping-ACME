"""Grid / image-first listing pattern.

Extracts detail links from listing pages that use image containers
like <div class="listing__image"> or similar.
"""
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate


class GridListingTemplate(CarTemplate):
    name = 'grid_listing'

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'lxml')
        urls = []
        # common image container
        for div in soup.select('div.listing__image, div.listing-image, div.image'):
            a = div.find('a')
            if a and a.get('href'):
                urls.append(urljoin(page_url, a['href']))
        # Dragon2000 stocklist pattern (sometimes grid pages use stocklist links)
        for a in soup.select('div.stocklist-vehicle a.vehicleLink[href]'):
            if a and a.get('href'):
                urls.append(urljoin(page_url, a['href']))
        # fallback: images with parent links
        for img in soup.find_all('img'):
            parent = img.find_parent('a')
            if parent and parent.get('href'):
                urls.append(urljoin(page_url, parent['href']))
        return list(dict.fromkeys(urls))

    def get_next_page(self, html: str, page_url: str):
        # listing templates generally don't implement pagination here
        return None

    def parse_car_page(self, html: str, car_url: str):
        raise NotImplementedError()
