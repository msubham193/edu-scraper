"""
scraper.py
----------
Fetches and scrapes each website URL.
- Rotates User-Agents
- Retries on failure
- Also scrapes /contact, /about pages for more data
"""

import time
import random
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from rich.console import Console
from extractor import extract_all

console = Console()
ua = UserAgent()

# Extra sub-pages to check for contact info
CONTACT_PATHS = ["/contact", "/contact-us", "/contactus", "/about",
                  "/about-us", "/reach-us", "/connect", "/enquiry"]

HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def _get_headers() -> dict:
    return {**HEADERS_BASE, "User-Agent": ua.random}


def _fetch(url: str, timeout: int = 15, retries: int = 3) -> str | None:
    """Fetch a URL with retries and rotating user-agents. Returns HTML or None."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=_get_headers(),
                timeout=timeout,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code in (403, 429, 401):
                # Blocked — no point retrying, move on immediately
                console.print(f"  [dim]Blocked ({resp.status_code}): {url}[/dim]")
                return None
            else:
                console.print(f"  [dim]HTTP {resp.status_code} for {url}[/dim]")
                return None
        except requests.exceptions.Timeout:
            console.print(f"  [dim]Timeout on {url} (attempt {attempt+1})[/dim]")
            time.sleep(2)
        except requests.exceptions.ConnectionError:
            console.print(f"  [dim]Connection error: {url}[/dim]")
            return None
        except Exception as e:
            console.print(f"  [dim]Error fetching {url}: {e}[/dim]")
            return None
    return None


def _find_contact_links(html: str, base_url: str) -> list[str]:
    """Find internal links that likely go to contact/about pages."""
    soup = BeautifulSoup(html, "lxml")
    links = set()
    keywords = {"contact", "about", "reach", "connect", "enquiry", "touch"}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.text.lower()
        if any(kw in href or kw in text for kw in keywords):
            full = urljoin(base_url, a["href"])
            # Only keep same-domain links
            if urlparse(full).netloc == urlparse(base_url).netloc:
                links.add(full)
    return list(links)[:5]  # Limit to 5 extra pages


def scrape_website(url: str) -> dict | None:
    """
    Scrape a single website:
    1. Fetch homepage
    2. Extract data
    3. Fetch contact/about sub-pages and merge extra data
    Returns a merged result dict or None if failed.
    """
    console.print(f"  [blue]Scraping:[/blue] {url}")

    # Fetch homepage
    html = _fetch(url)
    if not html:
        return None

    result = extract_all(html, url)

    # Find and scrape contact pages
    contact_links = _find_contact_links(html, url)

    # Also try common contact paths
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    for path in CONTACT_PATHS:
        candidate = base + path
        if candidate not in contact_links:
            contact_links.append(candidate)

    for contact_url in contact_links[:8]:  # Max 8 sub-pages
        time.sleep(random.uniform(0.5, 1.5))
        sub_html = _fetch(contact_url, timeout=10, retries=1)
        if sub_html:
            sub_data = extract_all(sub_html, contact_url)
            # Merge emails and phones
            result["emails"] = list(set(result["emails"] + sub_data["emails"]))
            result["phones"] = list(set(result["phones"] + sub_data["phones"]))

    # Final dedup & cleanup
    result["emails"] = sorted(set(result["emails"]))
    result["phones"] = sorted(set(result["phones"]))

    return result


def scrape_all(urls: list[str], delay: float = 2.0) -> list[dict]:
    """
    Scrape all URLs with a polite delay between requests.
    Returns list of result dicts.
    """
    from tqdm import tqdm
    results = []
    for url in tqdm(urls, desc="Scraping websites", unit="site"):
        result = scrape_website(url)
        if result:
            results.append(result)
        time.sleep(random.uniform(delay * 0.8, delay * 1.2))
    return results
