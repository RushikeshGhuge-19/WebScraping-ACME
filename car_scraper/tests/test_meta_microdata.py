"""Tests for detail templates with meta/microdata fallbacks."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from car_scraper.templates.detail_jsonld_vehicle import DetailJSONLDVehicle


def test_meta_tags():
    """Test detail_jsonld_vehicle with meta-tag fallback."""
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'car_meta.html'
    html = sample.read_text(encoding='utf-8')
    tpl = DetailJSONLDVehicle()
    out = tpl.parse_car_page(html, str(sample))
    assert out.get('price') == '7995' or out.get('_source') == 'meta-fallback'


def test_microdata():
    """Test detail_jsonld_vehicle with microdata fallback."""
    sample = Path(__file__).resolve().parent.parent / 'samples' / 'car_microdata.html'
    html = sample.read_text(encoding='utf-8')
    tpl = DetailJSONLDVehicle()
    out = tpl.parse_car_page(html, str(sample))
    assert out.get('_source') in ('microdata-fallback', 'json-ld') or out.get('price') == '5995'
