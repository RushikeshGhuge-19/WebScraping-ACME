"""Card-based listing pattern.

Extract links from card elements like <div class="vehicle-card">.
"""
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CarTemplate


class CardListingTemplate(CarTemplate):
    name = 'card_listing'

    def get_listing_urls(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'lxml')
        urls = []
        for card in soup.select('.vehicle-card, .car-card, .listing-card'):
            a = card.find('a')
            if a and a.get('href'):
                urls.append(urljoin(page_url, a['href']))
        # Dragon2000: stocklist pattern
        for a in soup.select('div.stocklist-vehicle a.vehicleLink[href]'):
            if a and a.get('href'):
                urls.append(urljoin(page_url, a['href']))
        return list(dict.fromkeys(urls))

    def get_next_page(self, html: str, page_url: str):
        return None

    def parse_car_page(self, html: str, car_url: str):
        raise NotImplementedError()
