"""Simple setup examples for using a proxy with requests+BeautifulSoup and Selenium.

Usage:
    python scripts/setup_proxy_bs_selenium.py

Configure the `PROXY` constant below. Example proxy formats:
- http://username:password@proxy-host:port
- http://proxy-host:port

Notes:
- Install dependencies from `requirements.txt` (added `requests`, `selenium`, `webdriver-manager`).
- Selenium will download ChromeDriver automatically via `webdriver-manager`.
"""
from typing import Optional
import requests
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Example proxy (replace with your proxy)
# PROXY = 'http://user:pass@1.2.3.4:8888'
PROXY: Optional[str] = None


def requests_with_proxy(url: str, proxy: Optional[str] = None):
    """Fetch a URL using requests via an HTTP(S) proxy and parse with BeautifulSoup."""
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; AcmeBot/1.0)'}
    if proxy:
        proxies = {'http': proxy, 'https': proxy}
        r = requests.get(url, headers=headers, proxies=proxies, timeout=15)
    else:
        r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')
    return soup


def selenium_with_proxy(url: str, proxy: Optional[str] = None, headless: bool = True):
    """Start a Chrome webdriver with an optional proxy and return page source parsed by BeautifulSoup.

    This example uses `webdriver-manager` to manage the ChromeDriver binary.
    """
    options = webdriver.ChromeOptions()
    if headless:
        # Use the new headless mode flag where available
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    if proxy:
        # Selenium expects a proxy server argument like --proxy-server=http://host:port
        options.add_argument(f'--proxy-server={proxy}')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        return soup
    finally:
        driver.quit()


if __name__ == '__main__':
    test_url = 'https://httpbin.org/headers'
    print('Running requests+BS4 example...')
    try:
        soup = requests_with_proxy(test_url, PROXY)
        print('Requests headers response snippet:')
        print(soup.prettify()[:1000])
    except Exception as e:
        print('Requests example failed:', e)

    print('\nRunning Selenium example... (this will download ChromeDriver if needed)')
    try:
        soup2 = selenium_with_proxy('https://httpbin.org/ip', PROXY, headless=True)
        print('Selenium page snippet:')
        print(soup2.prettify()[:1000])
    except Exception as e:
        print('Selenium example failed:', e)
