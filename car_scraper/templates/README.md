# Templates — car_scraper/templates

This folder contains the canonical parsing templates used by the scraping
engine. Each template implements a small, well-defined API (listing,
pagination, or detail) and is discovered by the detector using the
`ALL_TEMPLATES` list in `all_templates.py`.

**Purpose**
- Provide a set of reusable, small parsers for common car-dealer page
  patterns (JSON-LD, microdata, HTML spec tables, listing cards/grids,
  AJAX endpoints, etc.).

**Canonical templates included**
- Detail templates (emit car rows):
  - `detail_hybrid_json_html` — prefers JSON-LD, falls back to HTML specs
  - `detail_jsonld_vehicle` — parses Vehicle JSON-LD
  - `detail_inline_html_blocks` — parses dl/dt/dd and label/value blocks
  - `detail_html_spec_table` — parses tabular spec tables
  - `detail_image_gallery` — extracts gallery images & video sources
- Listing templates (do not emit CSV rows):
  - `listing_card` — card-based listings
  - `listing_image_grid` — image-first grid listings
  - `listing_section` — section-wrapped results
  - `listing_json_api` — extract URLs from embedded JSON/API payloads
  - `listing_ajax_infinite` — detect XHR / load-more endpoints
- Pagination templates (helpers): `pagination_query`, `pagination_path`
- Dealer/site template: `dealer_info_jsonld`

Detection order and registration
- The authoritative detection order is defined in `all_templates.py` as
  `ALL_TEMPLATES`. The detector and engine import this list to discover
  which template to run for a page. If you add a new template, also add it
  to `ALL_TEMPLATES` and export it from `__init__.py`.

How to add a new template
1. Create a subclass of `CarTemplate` in this folder.
2. Set the `name` attribute to a canonical string (snake_case).
3. Implement one or more of: `get_listing_urls`, `get_next_page`, `parse_car_page`.
4. Add the class to `all_templates.py` and export it from `__init__.py`.
5. Add a unit test under `car_scraper/tests/` using a sample HTML fixture.

Testing locally
- Run the sample runner (produces `scripts/sample_results.json`):

```powershell
E:\Scrapy\.venv\Scripts\python.exe scripts/test_templates_on_samples.py
```

- Run unit tests with pytest:

```powershell
E:\Scrapy\.venv\Scripts\python.exe -m pytest -q car_scraper/tests
```

Notes and best-practices
- Templates should avoid network I/O; prefer parsing embedded JSON and
  HTML. For sites that require JS execution, consider adding a single
  optional headless render step outside the template system.
- Keep templates focused: listing templates should only find listing URLs
  and pagination; detail templates should return normalized car fields.

If you need a template scaffold or a test example, I can create one for a
specific site or pattern. 
