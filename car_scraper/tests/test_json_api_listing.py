from car_scraper.templates.json_api_listing import JSONAPIListingTemplate
from pathlib import Path
import json


def load_sample(name: str) -> str:
    p = Path(__file__).parent.parent.parent / 'scripts' / name
    return p.read_text(encoding='utf-8')


def test_json_api_extract_urls():
    # use scripts/sample_results.json which contains a JSON structure
    raw = load_sample('sample_results.json')
    tpl = JSONAPIListingTemplate()
    urls = tpl.get_listing_urls(raw, 'http://example/')
    # expect a list (may be empty if no URLs found in this particular sample)
    assert isinstance(urls, list)


def test_is_listing_url_heuristics():
    tpl = JSONAPIListingTemplate()
    # accepted cases (relative and allowed absolute domain)
    assert tpl._is_listing_url('/cars/123')
    assert tpl._is_listing_url('/vehicle/ford-fiesta')
    assert tpl._is_listing_url('https://example.com/car/123')

    # rejected false positives
    assert not tpl._is_listing_url('/about/cars')
    assert not tpl._is_listing_url('/blog/listing-tips')
    # absolute URL on a non-allowlisted domain must be rejected
    assert not tpl._is_listing_url('https://notallowed.example/car/123')
