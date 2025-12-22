"""Simple Selenium-based renderer helpers.

Provides `render_url()` and `render_html()` convenience wrappers that
start a temporary headless Chrome instance using `webdriver-manager` and
return the fully rendered page source. The functions are intentionally
small and synchronous for use in sample runners and optional rendering
paths in the engine.
"""
from typing import Optional
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def _make_options(headless: bool = True, width: int = 1200, height: int = 800) -> Options:
    opts = Options()
    if headless:
        # modern chrome prefers --headless=new; keep compatibility
        opts.add_argument('--headless=new')
    opts.add_argument(f'--window-size={width},{height}')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    return opts


def render_url(url: str, wait: float = 1.0, headless: bool = True, timeout: int = 30) -> str:
    """Load `url` in a temporary Chrome instance and return final page source.

    `wait` gives the page a few seconds to execute JS. This is intentionally
    conservative; callers can increase wait time for heavy pages.
    """
    opts = _make_options(headless=headless)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        # simple wait to allow XHR/DOM updates; caller may tune
        if wait:
            time.sleep(wait)
        return driver.page_source
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def render_html(html: str, wait: float = 0.5, headless: bool = True, timeout: int = 30) -> str:
    """Render a raw HTML snippet by loading it via a data: URL in Chrome.

    Note: very large HTML blobs may hit URL length limits; prefer `render_url`
    when possible (for file:// paths or HTTP URLs).
    """
    # data: URL; ensure encoding is safe for basic HTML content.
    data_url = 'data:text/html;charset=utf-8,' + html
    return render_url(data_url, wait=wait, headless=headless, timeout=timeout)
