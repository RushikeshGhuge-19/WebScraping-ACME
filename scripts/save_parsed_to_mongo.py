"""Utility script: load `scripts/sample_results.json` and save parsed entries to MongoDB.

This is a small convenience for testing the `mongo_store` scaffold. It will
iterate samples -> templates and call `save_listing()` for any `parsed`
object present (non-null). By default it expects a MongoDB at
`mongodb://localhost:27017` but can be configured via `MONGO_URI` env var.
"""
import json
import os
from pathlib import Path
from car_scraper.db.mongo_store import save_listing

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = Path(ROOT) / 'scripts' / 'sample_results.json'

if not SAMPLE_FILE.exists():
    print('sample_results.json not found at', SAMPLE_FILE)
    raise SystemExit(1)

data = json.loads(SAMPLE_FILE.read_text(encoding='utf-8'))

count = 0
errors = 0
for sample_name, templates in data.items():
    for templ_name, entry in templates.items():
        parsed = entry.get('parsed')
        if not parsed:
            continue
        # attach provenance
        parsed = dict(parsed)
        parsed['_sample_file'] = sample_name
        parsed['_template'] = templ_name
        # attempt to set a url if available in raw or generated
        if not parsed.get('url'):
            # try to pick from _raw or tiers
            raw = parsed.get('_raw') or parsed.get('_raw_jsonld')
            if isinstance(raw, dict):
                if raw.get('url'):
                    parsed['url'] = raw['url']
                elif raw.get('offers') and isinstance(raw.get('offers'), dict):
                    parsed['url'] = raw['offers'].get('url')

        res = save_listing(parsed)
        if res.get('error'):
            errors += 1
            print('error saving', sample_name, templ_name, res)
        else:
            count += 1

print(f'saved {count} parsed docs ({errors} errors) to MongoDB at', os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))
