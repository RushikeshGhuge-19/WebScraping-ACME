"""Tests for the hybrid JSON+HTML template."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from car_scraper.templates.detail_hybrid_json_html import DetailHybridJSONHTML


def test_hybrid_parsing():
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'car_hybrid.html'
    html = sample.read_text(encoding='utf-8')
    tpl = DetailHybridJSONHTML()
    out = tpl.parse_car_page(html, str(sample))

    assert out.get('brand') == 'SampleBrand'
    assert out.get('model') == 'S-Model'
    assert out.get('price') == '12995'
    specs = out.get('specs')
    assert specs.get('mileage') == '30,000 miles'
    assert specs.get('fuel_type') == 'Petrol' or specs.get('fuel') == 'Petrol'
