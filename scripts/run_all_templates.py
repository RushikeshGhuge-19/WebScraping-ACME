"""Run all templates against sample files and generate a CSV report."""
from pathlib import Path
import csv
import argparse

from car_scraper.utils import renderer as _renderer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true', help='Use Selenium renderer for each sample (slow)')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    samples_dir = root / 'car_scraper' / 'samples'
    sample_files = sorted(list(samples_dir.glob('*.html')))

    from car_scraper.templates import all_templates

    print(f'Templates found: {len(all_templates.ALL_TEMPLATES)}')

    results = []
    rows = []
    
    for cls in all_templates.ALL_TEMPLATES:
        name = getattr(cls, 'name', cls.__name__)
        try:
            inst = cls()
        except Exception as e:
            results.append((name, 'init_error', str(e)))
            continue

        parse_ok = parse_err = list_ok = list_err = 0

        for sf in sample_files:
            try:
                if args.render:
                    # Use file:// URL so Chrome can load relative assets if needed
                    html = _renderer.render_url(f'file://{sf.resolve()}', wait=1.0)
                else:
                    html = sf.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                rows.append({
                    'sample': sf.name,
                    'template': name,
                    'parse_status': 'file_error',
                    'parse_summary': '',
                    'list_status': 'file_error',
                    'list_count': 0,
                    'error': repr(e),
                })
                continue

            parse_status = 'not_supported'
            parse_summary = ''
            list_status = 'not_supported'
            list_count = 0
            error_msg = ''

            # Try parse_car_page if available
            if hasattr(inst, 'parse_car_page'):
                try:
                    out = inst.parse_car_page(html, str(sf))
                    if isinstance(out, dict):
                        parse_status = 'ok'
                        parse_ok += 1
                        # Extract key fields for summary
                        parse_summary = str({
                            k: out.get(k) 
                            for k in ('name', 'brand', 'model', 'price', 'currency', 'mileage', 'year')
                        })
                    else:
                        parse_status = 'unexpected'
                        parse_err += 1
                        parse_summary = str(out)
                except Exception as e:
                    parse_status = 'error'
                    parse_err += 1
                    error_msg = repr(e)

            # Try get_listing_urls if available
            if hasattr(inst, 'get_listing_urls'):
                try:
                    urls = inst.get_listing_urls(html, str(sf))
                    if isinstance(urls, list):
                        list_status = 'ok'
                        list_count = len(urls)
                        list_ok += 1
                    else:
                        list_status = 'unexpected'
                        list_err += 1
                        if not error_msg:
                            error_msg = f"Expected list, got {type(urls).__name__}"
                except Exception as e:
                    list_status = 'error'
                    list_err += 1
                    list_error = repr(e)
                    error_msg = f"{error_msg}; {list_error}" if error_msg else list_error
            rows.append({
                'sample': sf.name,
                'template': name,
                'parse_status': parse_status,
                'parse_summary': parse_summary,
                'list_status': list_status,
                'list_count': list_count,
                'error': error_msg,
            })

        results.append((
            name, 'ok',
            {'parse_ok': parse_ok, 'parse_err': parse_err, 'list_ok': list_ok, 'list_err': list_err}
        ))

    # Write CSV of detailed rows
    out_csv = Path(__file__).resolve().parent / 'template_run_results.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=['sample', 'template', 'parse_status', 'parse_summary', 'list_status', 'list_count', 'error']
        )
        writer.writeheader()
        writer.writerows(rows)

    # Print summary
    print(f'\nDetailed CSV written to: {out_csv}')
    print('\nTemplate run summary:')
    for name, status, data in results:
        if status == 'init_error':
            print(f"- {name}: INIT ERROR -> {data}")
        else:
            print(f"- {name}: parse_ok={data['parse_ok']}, parse_err={data['parse_err']}, "
                  f"list_ok={data['list_ok']}, list_err={data['list_err']}")


if __name__ == '__main__':
    main()
