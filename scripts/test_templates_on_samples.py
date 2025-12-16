import sys
import os
import json
from pathlib import Path
sys.path.insert(0, r"e:\Scrapy")
from car_scraper.templates import ALL_TEMPLATES

SAMPLES_DIR = Path(r"e:/Scrapy/car_scraper/samples")
OUT_FILE = Path(r"e:/Scrapy/scripts/sample_results.json")

results = {}

html_files = sorted([p for p in SAMPLES_DIR.iterdir() if p.suffix.lower() == '.html'])
for path in html_files:
    name = path.name
    html = path.read_text(encoding='utf-8', errors='ignore')
    results[name] = {}
    for cls in ALL_TEMPLATES:
        templ_name = cls.name
        inst = cls()
        entry = {}
        # get_listing_urls
        try:
            urls = inst.get_listing_urls(html, str(path))
            entry['listing_urls'] = urls
        except NotImplementedError:
            entry['listing_urls'] = None
        except Exception as e:
            entry['listing_urls_error'] = repr(e)
        # get_next_page
        try:
            nxt = inst.get_next_page(html, str(path))
            entry['next_page'] = nxt
        except NotImplementedError:
            entry['next_page'] = None
        except Exception as e:
            entry['next_page_error'] = repr(e)
        # parse_car_page
        try:
            parsed = inst.parse_car_page(html, str(path))
            entry['parsed'] = parsed
        except NotImplementedError:
            entry['parsed'] = None
        except Exception as e:
            entry['parsed_error'] = repr(e)

        results[name][templ_name] = entry

OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('Wrote', OUT_FILE)
