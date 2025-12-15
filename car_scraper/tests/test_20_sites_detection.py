"""Detect which template each synthetic site sample maps to."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from car_scraper.engine import ScraperEngine


SAMPLES_EXPECTED = [
    ("site_listing_card_1.html", "listing_card"),
    ("site_listing_image_grid_2.html", "listing_image_grid"),
    ("site_listing_section_4.html", "listing_section"),
    ("site_detail_jsonld_vehicle_6.html", "detail_jsonld_vehicle"),
    ("site_detail_html_spec_table_7.html", "detail_html_spec_table"),
    ("site_detail_hybrid_json_html_8.html", "detail_hybrid_json_html"),
    ("site_detail_inline_html_blocks_9.html", "detail_inline_html_blocks"),
    ("site_detail_jsonld_variant_12.html", "detail_jsonld_vehicle"),
    ("site_detail_table_variant_13.html", "detail_html_spec_table"),
    ("site_listing_card_variant_14.html", "listing_card"),
    ("site_listing_image_grid_variant_15.html", "listing_image_grid"),
    ("site_detail_inline_variant_16.html", "detail_inline_html_blocks"),
    ("site_detail_table_variant_17.html", "detail_html_spec_table"),
    ("site_detail_hybrid_variant_18.html", "detail_hybrid_json_html"),
    ("site_dealer_info_jsonld_19.html", "dealer_info_jsonld"),
]


def test_detection_on_samples():
    engine = ScraperEngine()
    samples_dir = ROOT / 'samples'
    for fname, expected in SAMPLES_EXPECTED:
        p = samples_dir / fname
        # Skip if sample doesn't exist (synthetic samples may not be generated)
        if not p.exists():
            continue
        html = p.read_text(encoding='utf-8')
        tpl = engine.detector.detect(html, str(p))
        # detector returns a template with a name property
        name = getattr(tpl, 'name', None)
        assert name is not None, f"No template detected for {fname}"
        # Match on the expected canonical name
        assert expected in name, f"{fname}: expected {expected}, got {name}"
