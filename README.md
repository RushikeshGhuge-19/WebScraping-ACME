# Scrapy car templates

Lightweight template collection and parsers for scraping UK/EU car dealer sites.

This repository contains a small engine of HTML/JSON parsing templates used to
discover listings, parse vehicle detail pages, and extract dealer metadata.

## What’s included
- `car_scraper/templates/` — canonical templates (listing, detail, pagination, dealer)
  - Existing: card/grid/section listings, JSON-LD/microdata/meta fallbacks
  - Added: `listing_json_api`, `listing_ajax_infinite`, `detail_image_gallery`
- `car_scraper/db/mongo_store.py` — minimal MongoDB scaffold (upsert by `url`/`vin`)
- `scripts/` — helper scripts:
  - `run_template_smoke.py` — quick smoke test for a few templates
  - `test_templates_on_samples.py` — run every template against `car_scraper/samples`
  - `save_parsed_to_mongo.py` — load `scripts/sample_results.json` and save parsed docs to MongoDB
- `requirements.txt` — runtime dependencies

## Quick start

1. Create and activate a virtualenv (Windows example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
E:\Scrapy\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Run the smoke test:

```powershell
E:\Scrapy\.venv\Scripts\python.exe scripts/run_template_smoke.py
```

4. Run full sample pass (writes `scripts/sample_results.json`):

```powershell
E:\Scrapy\.venv\Scripts\python.exe scripts/test_templates_on_samples.py
```

5. Optionally save parsed results to MongoDB (set `MONGO_URI` to your DB):

```powershell
$env:MONGO_URI = 'mongodb://localhost:27017'
E:\Scrapy\.venv\Scripts\python.exe scripts/save_parsed_to_mongo.py
```

## MongoDB scaffold
The helper `car_scraper/db/mongo_store.py` uses `MONGO_URI`, `MONGO_DB`, and
`MONGO_COLLECTION` environment variables. `save_listing()` will upsert based on
`url` (preferred) or `vin` if present.

## Development notes
- Templates are intentionally conservative and do not execute JavaScript;
  they parse HTML and embedded JSON blocks. For heavy SPA pages you may need
  to add a headless render step or site-specific parsers.
- Add template classes to `car_scraper/templates/all_templates.py` to include
  them in the canonical detection order.

## Running tests
There are no formal unit tests yet. Use the sample runner in `scripts/` to
exercise templates against the provided sample HTML pages.

## Contributing
- Create a branch, add tests for new templates using `car_scraper/samples` as fixtures,
  and open a PR against `feature/add-templates-mongo` or main as appropriate.

## License
MIT-style (add appropriate LICENSE file if required).
