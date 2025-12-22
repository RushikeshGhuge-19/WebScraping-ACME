from car_scraper.templates import ListingCard, ListingImageGrid
from car_scraper.templates.detail_image_gallery import DetailImageGallery
from car_scraper.templates.dealer_info import DealerInfoTemplate


def test_listing_stocklist_selector_card():
    html = '<div class="stocklist-vehicle"><a class="vehicleLink" href="/detail/42">car</a></div>'
    tpl = ListingCard()
    urls = tpl.get_listing_urls(html, 'https://example.com')
    assert 'https://example.com/detail/42' in urls


def test_listing_stocklist_selector_grid():
    html = '<div class="stocklist-vehicle"><a class="vehicleLink" href="/g/99">x</a></div>'
    tpl = ListingImageGrid()
    urls = tpl.get_listing_urls(html, 'https://example.com')
    assert 'https://example.com/g/99' in urls


def test_detail_image_gallery_dragon2000():
    html = (
        '<div class="vehicle-content-slider--side-thumbs__carousel"><a href="/imgpage"><img src="/i.png"/></a></div>'
        '<div class="vehicle-content-slider--side-thumbs__thumbs-prev"><img data-src="/thumb.jpg"/></div>'
        '<div class="vehicle-content-slider-container"><a href="/img3.jpg">x</a></div>'
    )
    tpl = DetailImageGallery()
    out = tpl.parse_car_page(html, 'https://example.com/detail/1')
    imgs = out.get('images')
    assert 'https://example.com/imgpage' in imgs or 'https://example.com/i.png' in imgs
    assert 'https://example.com/thumb.jpg' in imgs
    assert 'https://example.com/img3.jpg' in imgs


def test_dealer_info_d2k_js_extracts_email():
    html = '<script>var d2k = { dealerDetails: { Email: "dealer@example.com" } };</script>'
    tpl = DealerInfoTemplate()
    out = tpl.parse_car_page(html, 'https://example.com')
    assert out.get('email') == 'dealer@example.com'
