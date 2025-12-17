"""car_scraper package init.

This module configures a small warnings filter to silence a known
DeprecationWarning emitted by BeautifulSoup's lxml builder on some
versions of lxml. It's safe to suppress here because the project
intentionally prefers `lxml` parsing and the warning is benign.
"""
import warnings

# Suppress lxml HTMLParser 'strip_cdata' deprecation noise coming from
# BeautifulSoup's lxml builder internals. The message text can vary
# between versions, so match substring with a regex.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*strip_cdata.*",
)
