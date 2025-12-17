"""Template registry, detector, and simple scraping engine.

This minimal engine is intended for offline parsing of saved HTML files.
It detects the most appropriate template for a page and dispatches parsing.
"""
from typing import List, Optional, Tuple, Dict, Any, Type
from pathlib import Path
from bs4 import BeautifulSoup
from .templates.utils import make_soup, extract_jsonld_objects

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
        # Use a single soup instance for all detection checks
        soup = make_soup(html)

        # quick signals
        has_table = bool(soup.find('table'))
        has_specs = bool(
            has_table
            or soup.select('.spec-row')
            or soup.select('.spec')
            or (soup.select('.label') and soup.select('.value'))
            or soup.select('.spec-block')
            or soup.select('dl')
        )

        jsonld_objs = extract_jsonld_objects(html)
        has_jsonld_vehicle = any(isinstance(o, dict) and (('Vehicle' in str(o.get('@type') or '')) or ('vehicle' in str(o.get('@type') or '').lower())) for o in jsonld_objs)

        # scoring across available templates
        candidates = []

        # Detail templates
        detail_mapping = {
            'detail_hybrid_json_html': 0,
            'detail_jsonld_vehicle': 0,
            'detail_inline_html_blocks': 0,
            'detail_html_spec_table': 0,
        }

        # hybrid: prefer JSON-LD + specs
        if has_jsonld_vehicle and has_specs:
            detail_mapping['detail_hybrid_json_html'] += 3

        # json-ld detail
        if has_jsonld_vehicle:
            detail_mapping['detail_jsonld_vehicle'] += 2

        # inline spec blocks
        if soup.select('.spec-row') or soup.select('.spec') or (soup.select('.label') and soup.select('.value')) or soup.find('dl'):
            detail_mapping['detail_inline_html_blocks'] += 1

        # spec table
        if has_table:
            detail_mapping['detail_html_spec_table'] += 1

        for name, base_score in detail_mapping.items():
            cls = TEMPLATE_BY_NAME.get(name)
            if cls:
                candidates.append((cls(), base_score))

        # Listing templates: score by number of discovered listing URLs
        for name in ('listing_image_grid', 'listing_card', 'listing_section'):
            cls = TEMPLATE_BY_NAME.get(name)
            if not cls:
                continue
            tpl = cls()
            try:
                urls = tpl.get_listing_urls(html, page_url)
                score = len(urls)
                candidates.append((tpl, score))
            except NotImplementedError:
                continue

        # Pagination templates: small score if next page found
        for name in ('pagination_query', 'pagination_path'):
            cls = TEMPLATE_BY_NAME.get(name)
            if not cls:
                continue
            tpl = cls()
            try:
                nxt = tpl.get_next_page(html, page_url)
                score = 1 if nxt else 0
                candidates.append((tpl, score))
            except NotImplementedError:
                continue

        # Dealer info fallback: modest score when Organization JSON-LD present
        dealer_cls = TEMPLATE_BY_NAME.get('dealer_info_jsonld')
        dealer_score = 0
        # look for Organization type in jsonld objects
        for o in jsonld_objs:
            t = o.get('@type') if isinstance(o, dict) else ''
            if 'Organization' in str(t) or 'AutomotiveBusiness' in str(t):
                dealer_score = 2
                break
        if dealer_cls:
            candidates.append((dealer_cls(), dealer_score))

        # choose best candidate (highest score). Ties resolved by original ALL_TEMPLATES order
        if not candidates:
            return None

        # compute max score
        max_score = max(score for _, score in candidates)
        # filter candidates with max_score
        best = [tpl for tpl, score in candidates if score == max_score]
        if len(best) == 1:
            return best[0]

        # tie-breaker: pick first in authoritative order
        for cls in self.registry.classes():
            for b in best:
                if isinstance(b, cls):
                    return b

        return best[0]


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
