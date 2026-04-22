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
    """Search Google using a Playwright page object with enhanced retry logic."""
    urls = []
    try:
        # Navigate to Google with increased timeout
        page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=45000)
        time.sleep(random.uniform(1.5, 2.5))

        # Accept cookies if prompted (common in India)
        try:
            accept_btn = page.locator("button:has-text('Accept all'), button:has-text('I agree'), button:has-text('Accept')")
            if accept_btn.count() > 0:
                accept_btn.first.click()
                time.sleep(1.5)
        except Exception:
            pass

        # Type query in search box with retries
        search_attempts = 0
        while search_attempts < 3:
            try:
                search_box = page.locator("textarea[name='q'], input[name='q']")
                if search_box.count() > 0:
                    search_box.first.click()
                    time.sleep(0.5)
                    search_box.first.fill(query)
                    time.sleep(0.5)
                    search_box.first.press("Enter")
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    time.sleep(random.uniform(2.5, 4))
                    break
                else:
                    search_attempts += 1
                    time.sleep(1)
            except Exception as e:
                search_attempts += 1
                console.print(f"[dim]Search attempt {search_attempts} failed: {e}[/dim]")
                time.sleep(2)

        if search_attempts >= 3:
            console.print(f"[yellow]Failed to search Google after 3 attempts[/yellow]")
            return urls

        pages_scraped = 0
        while len(urls) < num_results and pages_scraped < 5:
            try:
                # Extract all result links - Google result links: <a> tags inside <div class="yuRUbf"> or similar
                anchors = page.locator("div#search a[href]").all()
                if not anchors:
                    console.print(f"[dim]No anchors found on page[/dim]")
                    
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
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    time.sleep(random.uniform(2.5, 4))
                    pages_scraped += 1
                else:
                    break
            except Exception as e:
                console.print(f"[dim]Error during pagination: {e}[/dim]")
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
    Tries Google first with multiple retries, then Bing as fallback.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    console.print(f"[cyan]Searching for:[/cyan] [bold]{query}[/bold]")
    console.print("[dim]Launching headless browser...[/dim]")

    urls = []
    max_browser_retries = 2
    
    for browser_attempt in range(max_browser_retries):
        browser = None
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-blink-features=AutomationControlled",
                            "--disable-infobars",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                            "--disable-dev-tools",
                        ],
                        timeout=60000,  # Increased timeout for Render
                    )
                except Exception as e:
                    console.print(f"[yellow]Browser launch attempt {browser_attempt + 1} failed: {e}[/yellow]")
                    if browser_attempt < max_browser_retries - 1:
                        time.sleep(3)
                        continue
                    raise
                
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

                # Try Google first (with internal retries)
                console.print("[dim]Strategy 1: Google Search (Primary)...[/dim]")
                urls = _search_google_playwright(query, num_results, page)

                # Only use Bing as fallback if Google completely failed
                if not urls:
                    console.print("[yellow]Google search returned no results, trying Bing as fallback...[/yellow]")
                    urls = _search_bing_playwright(query, num_results, page)

                browser.close()
                break  # Success, exit retry loop
                
        except Exception as e:
            console.print(f"[red]Search attempt {browser_attempt + 1} failed: {e}[/red]")
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            if browser_attempt < max_browser_retries - 1:
                time.sleep(3)
            else:
                console.print("[red]All search attempts failed[/red]")
                raise

    console.print(f"[green]Found {len(urls)} valid URLs to scrape[/green]")
    if not urls:
        console.print("[red]WARNING: No URLs found - search may have failed[/red]")
    
    return urls
