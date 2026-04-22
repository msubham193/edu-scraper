"""
google_search.py
----------------
Uses Playwright headless Chromium browser to search Google.
This behaves like a real browser — bypasses all anti-bot blocks.
Falls back to Bing if Google fails.
"""

import time
import random
from urllib.parse import urlparse
from rich.console import Console

console = Console()

# Domains to skip (social media, maps, aggregators, portals)
SKIP_DOMAINS = {
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "maps.google.com", "google.com", "wikipedia.org",
    "justdial.com", "indiamart.com", "sulekha.com", "quora.com",
    "reddit.com", "yelp.com", "tripadvisor.com", "glassdoor.com",
    "shiksha.com", "collegedunia.com", "careers360.com",
    "practo.com", "amazon.com", "flipkart.com", "snapdeal.com",
    "naukri.com", "indeed.com", "paytm.com", "askiitians.com",
    "toppr.com", "byjus.com", "vedantu.com", "unacademy.com",
    "t.me", "wa.me", "whatsapp.com",
}


def _is_valid_url(url: str) -> bool:
    """Check if a URL points to a real institute website worth scraping."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        if not parsed.scheme.startswith("http"):
            return False
        if not domain or "." not in domain:
            return False
        for skip in SKIP_DOMAINS:
            if skip in domain:
                return False
        return True
    except Exception:
        return False


def _search_google_playwright(query: str, num_results: int, page) -> list[str]:
    """Search Google using a Playwright page object."""
    urls = []
    try:
        # Navigate to Google
        page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(random.uniform(1, 2))

        # Accept cookies if prompted (common in India)
        try:
            accept_btn = page.locator("button:has-text('Accept all'), button:has-text('I agree')")
            if accept_btn.count() > 0:
                accept_btn.first.click()
                time.sleep(1)
        except Exception:
            pass

        # Type query in search box
        search_box = page.locator("textarea[name='q'], input[name='q']")
        search_box.first.click()
        search_box.first.fill(query)
        search_box.first.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(random.uniform(2, 3))

        pages_scraped = 0
        while len(urls) < num_results and pages_scraped < 5:
            # Extract all result links
            # Google result links: <a> tags inside <div class="yuRUbf"> or similar
            anchors = page.locator("div#search a[href]").all()
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if href.startswith("http") and _is_valid_url(href) and href not in urls:
                        urls.append(href)
                        if len(urls) >= num_results:
                            break
                except Exception:
                    continue

            if len(urls) >= num_results:
                break

            # Try clicking "Next" button for next page
            next_btn = page.locator("a#pnnext, a[aria-label='Next page']")
            if next_btn.count() > 0:
                next_btn.first.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(random.uniform(2, 3))
                pages_scraped += 1
            else:
                break

    except Exception as e:
        console.print(f"[yellow]Google search error: {e}[/yellow]")

    return urls


def _search_bing_playwright(query: str, num_results: int, page) -> list[str]:
    """Search Bing as fallback using a Playwright page object."""
    urls = []
    try:
        page.goto(f"https://www.bing.com/search?q={query}&count=50", 
                  wait_until="domcontentloaded", timeout=30000)
        time.sleep(random.uniform(1.5, 2.5))

        pages_scraped = 0
        while len(urls) < num_results and pages_scraped < 5:
            # Bing result links are in <li class="b_algo"> -> <h2> -> <a>
            anchors = page.locator("li.b_algo h2 a").all()
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if href.startswith("http") and _is_valid_url(href) and href not in urls:
                        urls.append(href)
                        if len(urls) >= num_results:
                            break
                except Exception:
                    continue

            if len(urls) >= num_results:
                break

            # Next page
            next_btn = page.locator("a.sb_pagN, a[aria-label='Next page']")
            if next_btn.count() > 0:
                next_btn.first.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(random.uniform(1.5, 2.5))
                pages_scraped += 1
            else:
                break

    except Exception as e:
        console.print(f"[yellow]Bing search error: {e}[/yellow]")

    return urls


def google_search(query: str, num_results: int = 20) -> list[str]:
    """
    Master search function using Playwright headless Chromium.
    Tries Google first, then Bing as fallback.
    """
    from playwright.sync_api import sync_playwright

    console.print(f"[cyan]Searching for:[/cyan] [bold]{query}[/bold]")
    console.print("[dim]Launching headless browser...[/dim]")

    urls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        # Hide webdriver flag
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        # Try Google first
        console.print("[dim]Strategy 1: Google Search...[/dim]")
        urls = _search_google_playwright(query, num_results, page)

        # Fallback to Bing
        if not urls:
            console.print("[yellow]Google returned nothing, trying Bing...[/yellow]")
            urls = _search_bing_playwright(query, num_results, page)

        browser.close()

    console.print(f"[green]Found {len(urls)} valid URLs to scrape[/green]")
    return urls
