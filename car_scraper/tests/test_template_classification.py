from car_scraper.templates.all_templates import ALL_TEMPLATES
from pathlib import Path
import pytest

REQUIRED_DETAIL_KEYS = {
    'brand', 'model', 'year', 'price_value', 'price_raw', 'currency',
    'mileage_value', 'mileage_unit', 'fuel', 'transmission', 'description', 'raw'
}

# canonical detail template names
DETAIL_TEMPLATE_NAMES = {
    'detail_jsonld_vehicle', 'detail_html_spec_table',
    'detail_hybrid_json_html', 'detail_inline_html_blocks'
}

# Map each template to an appropriate sample file that showcases that template's
# parsing strategy. This ensures we test each template on real HTML structures
# that contain data in the format the template is designed to parse.
TEMPLATE_TO_SAMPLE = {
    'detail_hybrid_json_html': 'car_hybrid.html',
    'detail_jsonld_vehicle': 'car_jsonld.html',
    'detail_html_spec_table': 'car_html_table.html',
    'detail_inline_html_blocks': '2013 Brown Ford C-Max for sale for £995 in Romford, Essex.html',
    'detail_image_gallery': 'car_jsonld.html',  # fallback; image gallery is secondary
    'listing_image_grid': 'listing_grid.html',
    'listing_card': 'listing_card.html',
    'listing_ul_li': 'listing_grid.html',  # shares grid parsing logic
    'listing_generic_anchor': 'listing_grid.html',  # shares card parsing logic
    'listing_section': 'listing_section.html',
    'pagination_query': 'Used cars for sale. Barnoldswick & Lancashire car Dealer _ Anyvehicle.co.uk.html',
    'pagination_path': 'Used Cars for Sale _ Second Hand Cars _ Carwow.html',
    'dealer_info_jsonld': 'New Car Deals _ 75 Plates In Stock _ Autotrader.html',
}


def load_sample(name='car_jsonld.html'):
    root = Path(__file__).resolve().parents[1]
    p = root / 'samples' / name
    return p.read_text(encoding='utf-8')


def get_sample_for_template(tpl_cls):
    """Get the appropriate sample HTML file for testing a template.
    
    Each template is designed to parse specific HTML structures. This function
    returns a sample that contains real data in the format the template expects,
    ensuring we validate parsing logic (not just classification contracts).
    """
    tpl = tpl_cls()
    name = getattr(tpl, 'name', tpl_cls.__name__)
    sample_file = TEMPLATE_TO_SAMPLE.get(name, 'car_jsonld.html')
    return load_sample(sample_file)


@pytest.mark.parametrize('tpl_cls', ALL_TEMPLATES)
def test_template_classification_outputs(tpl_cls):
    """Enforce that only DETAIL templates output the canonical detail keys.
    
    This test validates the classification contract: detail templates must
    output all required keys, while non-detail templates must not output
    detail keys. Each template is tested against a sample HTML file that
    contains data in the format that template is designed to parse, ensuring
    we also validate parsing logic is functional.

    Non-detail templates must either raise NotImplementedError for
    `parse_car_page` or return data that does NOT contain the canonical
    detail keys.
    """
    html = get_sample_for_template(tpl_cls)
    tpl = tpl_cls()
    name = getattr(tpl, 'name', tpl_cls.__name__)

    try:
        out = tpl.parse_car_page(html, 'http://example/')
    except NotImplementedError:
        # listing/pagination templates commonly raise NotImplementedError
        # when parse_car_page is not implemented for their template type
        return
    # NOTE: do not swallow broad exceptions here — unexpected errors should
    # surface so template bugs or broken mappings are visible in test output.

    if name in DETAIL_TEMPLATE_NAMES:
        assert isinstance(out, dict), f"{name} must return a dict"
        missing = REQUIRED_DETAIL_KEYS - set(out.keys())
        assert not missing, f"{name} missing keys: {missing}"
    else:
        # Non-detail templates should not include detail keys
        if isinstance(out, dict):
            intersection = REQUIRED_DETAIL_KEYS & set(out.keys())
            assert not intersection, f"Non-detail template {name} returned detail keys: {intersection}"