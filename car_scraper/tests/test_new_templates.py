from car_scraper.templates.json_api_listing import ListingJSONAPITemplate
from car_scraper.templates.ajax_infinite_listing import ListingAjaxInfiniteTemplate
from car_scraper.templates.detail_image_gallery import DetailImageGallery


def test_json_api_listing_extracts_urls():
    html = '<html><script type="application/json">{"items":[{"url":"/car/123","title":"X"}]}</script></html>'
    tpl = ListingJSONAPITemplate()
    urls = tpl.get_listing_urls(html, 'https://example.com')
    assert urls == ['https://example.com/car/123']


def test_ajax_infinite_listing_finds_fetch_and_anchor():
    html = '<html><script>fetch("/api/listing?page=2")</script><a href="/used-cars?page=3">more</a></html>'
    tpl = ListingAjaxInfiniteTemplate()
    urls = tpl.get_listing_urls(html, 'https://example.com')
    assert 'https://example.com/api/listing?page=2' in urls
    assert 'https://example.com/used-cars?page=3' in urls


def test_detail_image_gallery_collects_images():
    html = (
        '<html>'
        '<script type="application/ld+json">{"@type":"Product","image":["/img1.jpg","/img2.jpg"]}</script>'
        '<img src="/thumb.jpg" data-large="/large.jpg"/>'
        '</html>'
    )
    tpl = DetailImageGallery()
    out = tpl.parse_car_page(html, 'https://example.com/detail/1')
    imgs = out.get('images')
    assert 'https://example.com/img1.jpg' in imgs
    assert 'https://example.com/img2.jpg' in imgs
    assert 'https://example.com/large.jpg' in imgs
