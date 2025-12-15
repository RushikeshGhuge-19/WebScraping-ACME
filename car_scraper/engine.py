"""Template registry, detector, and simple scraping engine.

This minimal engine is intended for offline parsing of saved HTML files.
It detects the most appropriate template for a page and dispatches parsing.
"""
from typing import List, Optional, Tuple, Dict, Any, Type
from pathlib import Path
from bs4 import BeautifulSoup

from .templates.all_templates import ALL_TEMPLATES, TEMPLATE_BY_NAME


class TemplateRegistry:
    """Holds available template classes in detection order."""

    def __init__(self):
        # detection order comes from the centralized ALL_TEMPLATES list
        self._order = list(ALL_TEMPLATES)

    def classes(self) -> List[Type]:
        return self._order


class TemplateDetector:
    """Simple heuristic detector that picks the best template for HTML."""

    def __init__(self, registry: TemplateRegistry):
        self.registry = registry

    def detect(self, html: str, page_url: str):
        soup = BeautifulSoup(html, 'lxml')

        # Detection order (strict, authoritative):
        # 1) hybrid detail (json-ld + visible specs),
        # 2) json-ld detail,
        # 3) inline spec blocks detail,
        # 4) html spec table detail,
        # 5) listing patterns (do NOT emit rows),
        # 6) pagination (no rows),
        # 7) dealer info (site-level)

        has_specs = bool(
            soup.find('table')
            or soup.select('.spec-row')
            or soup.select('.spec')
            or (soup.select('.label') and soup.select('.value'))
            or soup.select('.spec-block')
            or soup.select('dl')
        )

        # hybrid: JSON-LD + specs
        if soup.find('script', type='application/ld+json') and has_specs:
            cls = TEMPLATE_BY_NAME.get('detail_hybrid_json_html')
            return cls() if cls else None

        # json-ld detail
        for script in soup.find_all('script', type='application/ld+json'):
            text = script.string or ''
            if 'Vehicle' in text or 'vehicle' in text.lower():
                cls = TEMPLATE_BY_NAME.get('detail_jsonld_vehicle')
                return cls() if cls else None

        # inline spec blocks (label/value divs or dl/dt/dd)
        if soup.select('.spec-row') or soup.select('.spec') or (soup.select('.label') and soup.select('.value')) or soup.find('dl'):
            cls = TEMPLATE_BY_NAME.get('detail_inline_html_blocks')
            return cls() if cls else None

        # spec table
        if soup.find('table'):
            cls = TEMPLATE_BY_NAME.get('detail_html_spec_table')
            return cls() if cls else None

        # listing patterns
        for name in ('listing_image_grid', 'listing_card', 'listing_section'):
            cls = TEMPLATE_BY_NAME.get(name)
            if not cls:
                continue
            tpl = cls()
            try:
                urls = tpl.get_listing_urls(html, page_url)
                if urls:
                    return tpl
            except NotImplementedError:
                continue

        # pagination
        for name in ('pagination_query', 'pagination_path'):
            cls = TEMPLATE_BY_NAME.get(name)
            if not cls:
                continue
            tpl = cls()
            try:
                nxt = tpl.get_next_page(html, page_url)
                if nxt:
                    return tpl
            except NotImplementedError:
                continue

        # dealer info fallback (site-level)
        cls = TEMPLATE_BY_NAME.get('dealer_info_jsonld')
        return cls() if cls else None


class ScraperEngine:
    """Runs detection and parsing on saved HTML files.

    Example usage:
        engine = ScraperEngine()
        engine.scrape_samples(Path('car_scraper/samples'))
    """

    def __init__(self):
        self.registry = TemplateRegistry()
        self.detector = TemplateDetector(self.registry)

    def scrape_file(self, file_path: Path) -> Dict[str, Any]:
        """Detect template and return structured output dict with explicit
        keys: 'car' for car detail dicts, 'dealer' for dealer info dicts.

        Listing and pagination templates do not create rows; they may provide
        'listing_urls' for downstream crawlers but those are NOT emitted to
        CSV by the runner.
        """
        html = file_path.read_text(encoding='utf-8')
        tpl = self.detector.detect(html, str(file_path))
        result: Dict[str, Any] = {'sample': file_path.name, 'template': tpl.name}

        car = None
        dealer = None
        listing_urls = None

        # Allowed detail templates names (authoritative)
        detail_names = {
            'detail_jsonld_vehicle',
            'detail_html_spec_table',
            'detail_hybrid_json_html',
            'detail_inline_html_blocks',
        }

        # Listing templates (do not emit rows)
        listing_names = {'listing_card', 'listing_image_grid', 'listing_section'}

        # Pagination templates (no rows)
        pagination_names = {'pagination_query', 'pagination_path'}

        # Dealer template name
        dealer_name = 'dealer_info_jsonld'

        try:
            parsed = tpl.parse_car_page(html, str(file_path))
        except NotImplementedError:
            parsed = None

        # If this template is a detail template, treat parsed as car
        if tpl.name in detail_names:
            car = parsed
        elif tpl.name == dealer_name:
            dealer = parsed
        elif tpl.name in listing_names:
            # try to extract listing URLs but do not produce car rows here
            try:
                listing_urls = tpl.get_listing_urls(html, str(file_path))
            except Exception:
                listing_urls = None
        elif tpl.name in pagination_names:
            # pagination: no rows
            pass
        else:
            # Unknown/unsupported template: do not let it emit car rows.
            # If it returned parsed data, keep it for debugging but do not
            # treat as car/dealer emission.
            if parsed:
                result['parsed_debug'] = parsed

        result['car'] = car
        result['dealer'] = dealer
        if listing_urls:
            result['listing_urls'] = listing_urls
        return result

    def scrape_samples(self, samples_dir: Path) -> List[Dict[str, Any]]:
        out = []
        for p in sorted(samples_dir.glob('*.html')):
            out.append(self.scrape_file(p))
        return out
