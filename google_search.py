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

# Domains to skip (social media, maps, aggregators, portals, and search engines)
SKIP_DOMAINS = {
    # Search engines — must never appear as results
    "google.com", "bing.com", "microsoft.com", "msn.com", "yahoo.com",
    "duckduckgo.com", "baidu.com", "yandex.com", "ask.com",
    # Social / messaging
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "t.me", "wa.me", "whatsapp.com", "pinterest.com",
    # Maps / travel
    "maps.google.com", "tripadvisor.com",
    # Reference / Q&A
    "wikipedia.org", "quora.com", "reddit.com",
    # Indian aggregators / directories
    "justdial.com", "indiamart.com", "sulekha.com", "glassdoor.com",
    "shiksha.com", "collegedunia.com", "careers360.com", "askiitians.com",
    "naukri.com", "indeed.com", "yelp.com",
    # Ecommerce / payments
    "practo.com", "amazon.com", "flipkart.com", "snapdeal.com", "paytm.com",
    # EdTech platforms (not institutes themselves)
    "toppr.com", "byjus.com", "vedantu.com", "unacademy.com",
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
        # Reject search-engine internal links (e.g. bing.com/search, google.com/search)
        search_paths = ["/search", "/Search", "/images", "/maps", "/news", "/video", "/shopping"]
        for sp in search_paths:
            if parsed.path.startswith(sp):
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
        time.sleep(random.uniform(2, 3))

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
                    time.sleep(random.uniform(0.5, 1.5))
                    search_box.first.type(query, delay=50)  # Slower typing = more human-like
                    time.sleep(0.5)
                    search_box.first.press("Enter")
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    time.sleep(random.uniform(3, 5))
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
        
        # Check for captcha/block page
        try:
            title = page.title()
            if "captcha" in title.lower() or "unusual traffic" in page.content().lower():
                console.print("[red]⚠️  Google detected unusual traffic (possible bot detection)[/red]")
                return urls
        except Exception:
            pass

        pages_scraped = 0
        while len(urls) < num_results and pages_scraped < 5:
            try:
                # Try multiple selectors for Google result links (HTML structure varies)
                # Google wraps result links as /url?q=<actual_url>
                anchors = page.locator("a[href*='/url?q=']").all()
                
                if not anchors or len(anchors) < 3:
                    # Fallback to alternative selectors
                    anchors = page.locator("div#search div.g a[href^='http']").all()
                
                if not anchors or len(anchors) < 3:
                    # Last resort: look for any links in search results
                    anchors = page.locator("div#search a:not([aria-label='Search by voice']):not([aria-label='Search'])").all()
                
                if not anchors:
                    console.print(f"[yellow]No Google results found on page - this may indicate bot detection[/yellow]")
                    break
                    
                console.print(f"[dim]Found {len(anchors)} potential result links[/dim]")
                
                for a in anchors:
                    try:
                        href = a.get_attribute("href") or ""
                        
                        # Unwrap Google's /url?q= wrapper if present
                        if "/url?q=" in href:
                            href = href.split("/url?q=")[1].split("&")[0]
                        
                        if href.startswith("http") and _is_valid_url(href) and href not in urls:
                            urls.append(href)
                            if len(urls) >= num_results:
                                break
                    except Exception as e:
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
        from urllib.parse import quote_plus
        page.goto(
            f"https://www.bing.com/search?q={quote_plus(query)}&count=50&setlang=en-IN",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(random.uniform(2.0, 3.5))

        pages_scraped = 0
        while len(urls) < num_results and pages_scraped < 5:
            # Try multiple robust selectors for Bing results
            selectors = [
                "li.b_algo h2 a",           # Classic Bing layout
                "li.b_algo .b_title a",     # Alternative layout
                "#b_results li.b_algo a",   # Broader fallback
            ]
            anchors = []
            for sel in selectors:
                anchors = page.locator(sel).all()
                if len(anchors) > 2:
                    break

            if not anchors:
                console.print("[yellow]Bing: No result anchors found — possible layout change[/yellow]")
                break

            console.print(f"[dim]Bing: found {len(anchors)} candidate links[/dim]")

            for a in anchors:
                try:
                    href = (a.get_attribute("href") or "").strip()
                    if not href.startswith("http"):
                        continue
                    # Hard-reject any Bing / Microsoft / search-engine URL
                    parsed_href = urlparse(href)
                    raw_domain = parsed_href.netloc.lower().replace("www.", "")
                    if any(se in raw_domain for se in ["bing.com", "microsoft.com", "msn.com", "google.com"]):
                        continue
                    if _is_valid_url(href) and href not in urls:
                        urls.append(href)
                        console.print(f"[dim]  ✓ Bing result: {href[:80]}[/dim]")
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
                time.sleep(random.uniform(2.0, 3.5))
                pages_scraped += 1
            else:
                break

    except Exception as e:
        console.print(f"[yellow]Bing search error: {e}[/yellow]")

    return urls


def google_search(query: str, num_results: int = 20) -> list[str]:
    """
    Master search function using Playwright headless Chromium.
    Tries Google first with multiple retries. Bing is LAST RESORT only.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    console.print(f"[cyan]Searching for:[/cyan] [bold]{query}[/bold]")
    console.print("[dim]Launching headless browser...[/dim]")

    urls = []
    max_browser_retries = 2
    google_attempts = 0
    
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
                    http_credentials=None,  # Don't send credentials
                )
                # Hide webdriver flag and other detection vectors
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
                """)

                page = context.new_page()

                # Try Google first (multiple attempts)
                google_attempts = 0
                max_google_attempts = 2
                while google_attempts < max_google_attempts and not urls:
                    google_attempts += 1
                    console.print(f"[dim]Attempt {google_attempts}/{max_google_attempts}: Searching Google...[/dim]")
                    urls = _search_google_playwright(query, num_results, page)
                    if urls:
                        console.print(f"[green]✓ Google search successful: Found {len(urls)} results[/green]")
                        break
                    if google_attempts < max_google_attempts:
                        console.print("[dim]No results from Google, retrying...[/dim]")
                        time.sleep(3)

                # If Google completely failed (not just 0 results), try Bing as ABSOLUTE last resort
                if not urls and google_attempts >= max_google_attempts:
                    console.print("[yellow]⚠️  Google search exhausted. Attempting Bing as fallback...[/yellow]")
                    urls = _search_bing_playwright(query, num_results, page)
                    if urls:
                        console.print(f"[yellow]Bing fallback found {len(urls)} results[/yellow]")

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
                console.print("[dim]Retrying entire search session...[/dim]")
                time.sleep(3)

    console.print(f"[green]Search complete: Found {len(urls)} valid URLs to scrape[/green]")
    if not urls:
        console.print("[red]✗ WARNING: No URLs found from any search engine - search may have been blocked[/red]")
    
    return urls
