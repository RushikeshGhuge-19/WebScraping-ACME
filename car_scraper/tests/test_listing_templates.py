"""Tests for listing templates (grid, card, section) and pagination helpers."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from car_scraper.templates.grid_listing import GridListingTemplate
from car_scraper.templates.card_listing import CardListingTemplate
from car_scraper.templates.section_listing import SectionListingTemplate
from car_scraper.templates.pagination_query import PaginationQueryTemplate
from car_scraper.templates.pagination_path import PaginationPathTemplate

def test_grid_listing_urls():
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'listing_grid.html'
    html = sample.read_text(encoding='utf-8')
    tpl = GridListingTemplate()
    urls = tpl.get_listing_urls(html, 'https://example.com/list')
    assert '/car/1' in urls[0] or 'car/1' in urls[0]


def test_card_listing_urls():
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'listing_card.html'
    html = sample.read_text(encoding='utf-8')
    tpl = CardListingTemplate()
    urls = tpl.get_listing_urls(html, 'https://example.com/list')
    assert any('car/10' in u for u in urls)


def test_section_listing_urls():
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'listing_section.html'
    html = sample.read_text(encoding='utf-8')
    tpl = SectionListingTemplate()
    urls = tpl.get_listing_urls(html, 'https://example.com/list')
    assert any('car/20' in u for u in urls)


def test_pagination_query_nextpage():
    html = '<a href="?page=2">Next</a>'
    tpl = PaginationQueryTemplate()
    nxt = tpl.get_next_page(html, 'https://example.com/list?page=1')
    assert nxt is not None


def test_pagination_path_nextpage():
    html = '<a href="/used-cars/page/3">3</a>'
    tpl = PaginationPathTemplate()
    nxt = tpl.get_next_page(html, 'https://example.com/used-cars/page/2')
    assert nxt is not None
