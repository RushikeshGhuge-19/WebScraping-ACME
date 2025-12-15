"""Aggregator for the authoritative template set.

Provides a single place that lists the canonical templates used by the
engine so we can import one module to get the full set.
"""
from .listing_card import ListingCard
from .listing_image_grid import ListingImageGrid
from .section_listing import SectionListingTemplate as ListingSection

from .detail_jsonld_vehicle import DetailJSONLDVehicle
from .detail_html_spec_table import DetailHTMLSpecTable
from .detail_hybrid_json_html import DetailHybridJSONHTML
from .detail_inline_html_blocks import DetailInlineHTMLBlocks

from .pagination_query import PaginationQueryTemplate
from .pagination_path import PaginationPathTemplate

from .dealer_info_jsonld import DealerInfoJSONLD


# Authoritative detection order (detail first, then listings/pagination, then dealer)
ALL_TEMPLATES = [
    DetailHybridJSONHTML,
    DetailJSONLDVehicle,
    DetailInlineHTMLBlocks,
    DetailHTMLSpecTable,
    ListingImageGrid,
    ListingCard,
    ListingSection,
    PaginationQueryTemplate,
    PaginationPathTemplate,
    DealerInfoJSONLD,
]

# Map by canonical template name -> class
TEMPLATE_BY_NAME = {cls.name: cls for cls in ALL_TEMPLATES}

__all__ = ["ALL_TEMPLATES", "TEMPLATE_BY_NAME"]
