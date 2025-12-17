"""Tests for the TemplateDetector scoring behavior."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from car_scraper.engine import TemplateDetector, TemplateRegistry


def test_detector_prefers_jsonld_hybrid():
    # JSON-LD vehicle + table specs should pick hybrid
    html = '<script type="application/ld+json">{"@type": "Vehicle", "name": "X"}</script><table><tr><th>Mileage</th><td>12,000 miles</td></tr></table>'
    detector = TemplateDetector(TemplateRegistry())
    tpl = detector.detect(html, 'https://example.com/sample')
    assert tpl is not None
    assert tpl.name in ('detail_hybrid_json_html', 'detail_jsonld_vehicle')


def test_detector_listing_detection():
    html = '<div class="vehicle-card"><a href="/car/1">link</a></div>'
    detector = TemplateDetector(TemplateRegistry())
    tpl = detector.detect(html, 'https://example.com/list')
    assert tpl is not None
    assert tpl.name in ('listing_card', 'listing_image_grid', 'listing_section')
