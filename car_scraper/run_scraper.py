"""Simple runner to apply available templates to saved HTML samples.

This runner loads each .html file in `car_scraper/samples/` and attempts
to parse it with the JSON-LD and HTML spec-table templates. Results are
printed to stdout for inspection.
"""
from pathlib import Path
from pprint import pprint
from typing import List

from car_scraper.templates.detail_jsonld_vehicle import DetailJSONLDVehicle
from car_scraper.templates.detail_html_spec_table import DetailHTMLSpecTable


def find_samples(samples_dir: Path) -> List[Path]:
    return sorted(p for p in samples_dir.glob('*.html'))


def main():
    root = Path(__file__).resolve().parent
    samples_dir = root / 'samples'
    samples = find_samples(samples_dir)
    jsonld_tpl = DetailJSONLDVehicle()
    table_tpl = DetailHTMLSpecTable()

    for sample in samples:
        print('---')
        print('Sample:', sample.name)
        html = sample.read_text(encoding='utf-8')

        print('\nJSON-LD template output:')
        try:
            out_jsonld = jsonld_tpl.parse_car_page(html, str(sample))
            pprint(out_jsonld)
        except Exception as e:
            print('Error parsing JSON-LD:', e)

        print('\nHTML-spec-table template output:')
        try:
            out_table = table_tpl.parse_car_page(html, str(sample))
            pprint(out_table)
        except Exception as e:
            print('Error parsing HTML table:', e)


if __name__ == '__main__':
    main()
