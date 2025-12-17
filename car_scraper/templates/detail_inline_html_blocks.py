"""Detail template parsing inline label/value blocks and fallbacks.

This template extracts specs from common inline structures (dl/dt/dd,
label/value pairs, .label/.value, .spec-row) and also includes meta-tag
and microdata fallbacks when explicit structured data is missing.
"""
from typing import Dict, Any
from bs4 import BeautifulSoup
import re
import html as _html
from .base import CarTemplate
from .utils import parse_mileage, parse_year, normalize_brand


class DetailInlineHTMLBlocks(CarTemplate):
    name = 'detail_inline_html_blocks'

    def _meta_fallback(self, soup: BeautifulSoup) -> Dict[str, Any]:
        out: Dict[str, Any] = {'_source': 'meta-fallback'}

        def meta(name=None, prop=None):
            if prop:
                tag = soup.find('meta', attrs={'property': prop})
                if tag and tag.get('content'):
                    return tag['content']
            if name:
                tag = soup.find('meta', attrs={'name': name})
                if tag and tag.get('content'):
                    return tag['content']
            return None

        out['title'] = meta(prop='og:title') or meta(name='title') or (soup.title.string if soup.title else None)
        out['price'] = meta(prop='product:price:amount') or meta(name='price')
        out['currency'] = meta(prop='product:price:currency') or meta(name='currency')
        out['description'] = meta(prop='og:description') or meta(name='description')
        return out

    def _microdata_fallback(self, soup: BeautifulSoup) -> Dict[str, Any]:
        out: Dict[str, Any] = {'_source': 'microdata-fallback'}
        for tag in soup.find_all(attrs={"itemscope": True}):
            it = tag.get('itemtype') or ''
            if 'Vehicle' in it or 'vehicle' in it.lower():
                for prop in ('name', 'brand', 'model', 'description', 'price'):
                    node = tag.find(attrs={'itemprop': prop})
                    if node:
                        out[prop] = node.get_text(strip=True)
                price_meta = tag.find('meta', attrs={'itemprop': 'price'})
                if price_meta and price_meta.get('content'):
                    out['price'] = price_meta['content']
                return out
        return out

    def parse_car_page(self, html: str, car_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'lxml')
        out: Dict[str, Any] = {'_source': 'inline-blocks', 'specs': {}}

        # Extract dl/dt/dd
        dl = soup.find('dl')
        if dl:
            dts = dl.find_all('dt')
            for dt in dts:
                dd = dt.find_next_sibling('dd')
                if not dd:
                    continue
                key = dt.get_text(separator=' ').strip()
                val = dd.get_text(separator=' ').strip()
                nk = re.sub(r"[^a-z0-9]+", '_', key.lower()).strip('_')
                out['specs'][nk] = val
                if 'mileage' in key.lower() and 'mileage' not in out:
                    out['mileage'] = val
                    m_val, m_unit = parse_mileage(val)
                    if m_val:
                        out['mileage_value'] = m_val
                        out['mileage_unit'] = m_unit
                if 'fuel' in key.lower() and 'fuel' not in out:
                    out['fuel'] = val
                if 'transmission' in key.lower() and 'transmission' not in out:
                    out['transmission'] = val

        # label/value pairs (.label/.value or .spec-row)
        for label in soup.select('.label'):
            val = None
            # common structure: <div class="label">Year</div><div class="value">2018</div>
            nxt = label.find_next_sibling()
            if nxt and 'value' in (nxt.get('class') or []):
                val = nxt.get_text(strip=True)
            else:
                # try within same parent
                val = label.parent.select_one('.value')
                if val:
                    val = val.get_text(strip=True)
            if val:
                key = label.get_text(separator=' ').strip()
                nk = re.sub(r"[^a-z0-9]+", '_', key.lower()).strip('_')
                out['specs'][nk] = val
                if 'mileage' in key.lower() and 'mileage' not in out:
                    m_val, m_unit = parse_mileage(val)
                    if m_val:
                        out['mileage_value'] = m_val
                        out['mileage_unit'] = m_unit

        # .spec-row style: <div class="spec-row"><span class="spec">Label</span><span class="value">Val</span></div>
        for row in soup.select('.spec-row'):
            lab = row.select_one('.spec') or row.select_one('th')
            valn = row.select_one('.value') or row.select_one('td')
            if lab and valn:
                key = lab.get_text(separator=' ').strip()
                val = valn.get_text(separator=' ').strip()
                nk = re.sub(r"[^a-z0-9]+", '_', key.lower()).strip('_')
                out['specs'][nk] = val
                if 'mileage' in key.lower() and 'mileage' not in out:
                    m_val, m_unit = parse_mileage(val)
                    if m_val:
                        out['mileage_value'] = m_val
                        out['mileage_unit'] = m_unit

        # If we found no inline data, try microdata then meta as fallbacks
        if not out['specs']:
            micro = self._microdata_fallback(soup)
            if micro and len(micro) > 1:
                out.update(micro)
                return out
            meta = self._meta_fallback(soup)
            if meta and (meta.get('price') or meta.get('title')):
                out.update(meta)
                return out

        # normalize brand/year if provided in specs
        if out.get('specs'):
            if out['specs'].get('brand') and not out.get('brand'):
                out['brand'] = normalize_brand(out['specs'].get('brand'))
            if out['specs'].get('year'):
                y = parse_year(out['specs'].get('year'))
                if y:
                    out['year'] = y

        return out
