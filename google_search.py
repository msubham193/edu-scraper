"""
google_search.py
----------------
Uses Playwright headless Chromium browser to search Google.
This behaves like a real browser — bypasses all anti-bot blocks.
Falls back to Bing if Google fails.
"""

import os
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


def _search_serper_api(query: str, num_results: int) -> list[str]:
    """
    Lightning-fast robust search using Serper.dev API.
    Bypasses all Google Captchas and IP blocks on AWS EC2.
    """
    import requests as _req
    import json
    
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return []

    urls = []
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "q": query,
        "gl": "in",      # Country: India
        "hl": "en",      # Language: English
        "num": 100       # Fetch 100 raw results to guarantee we have enough after filtering out portals/directories
    })

    try:
        console.print("[dim]⚡ Using Serper.dev API (Instant, No-Block)...[/dim]")
        resp = _req.post("https://google.serper.dev/search", headers=headers, data=payload, timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        organic_results = data.get("organic", [])
        
        for item in organic_results:
            href = item.get("link", "")
            if href.startswith("http") and _is_valid_url(href) and href not in urls:
                urls.append(href)
                if len(urls) >= num_results:
                    break
                    
        if urls:
            console.print(f"[green]✓ Serper API found {len(urls)} valid results instantly[/green]")
        else:
            console.print("[yellow]Serper API returned 0 valid institute URLs.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Serper API Error: {e}[/red]")
        
    return urls


def _search_duckduckgo_requests(query: str, num_results: int) -> list[str]:
    """
    Fast primary search using DuckDuckGo's HTML endpoint.
    Uses plain requests — NO Playwright, NO browser.
    Completes in 1-3 seconds. Works on EC2 without bot detection.
    """
    import requests as _req
    from bs4 import BeautifulSoup as _BS
    from urllib.parse import unquote as _unquote, parse_qs as _parse_qs, urlparse as _urlparse

    urls = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    try:
        console.print("[dim]🦆 Trying DuckDuckGo (fast, no browser)...[/dim]")
        # DDG HTML endpoint — POST request with the search query
        resp = _req.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "in-en"},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        soup = _BS(resp.text, "lxml")

        # DDG wraps result URLs in a redirect: /l/?uddg=<encoded_url>&...
        for a in soup.select("a.result__a"):
            href = (a.get("href") or "").strip()
            # Decode DDG redirect wrapper
            if "uddg=" in href:
                qs = _parse_qs(_urlparse(href).query)
                href = _unquote(qs.get("uddg", [""])[0])
            if href.startswith("http") and _is_valid_url(href) and href not in urls:
                urls.append(href)
                if len(urls) >= num_results:
                    break

        if urls:
            console.print(f"[green]✓ DuckDuckGo found {len(urls)} results in ~1s[/green]")
        else:
            console.print("[yellow]DuckDuckGo returned 0 results — may need browser fallback[/yellow]")

    except Exception as e:
        console.print(f"[yellow]DuckDuckGo search failed: {e}[/yellow]")

    return urls


def google_search(query: str, num_results: int = 20) -> list[str]:
    """
    Master search function.
    Priority:
      0. Serper.dev API (Ultra-fast, bulletproof) — HIGH PRIORITY (If KEY exists)
      1. DuckDuckGo HTML (fast, no browser, ~1-3s) — FALLBACK 1
      2. Google via Playwright (slow, 30-60s, may be blocked on EC2) — FALLBACK 2
      3. Bing via Playwright (slow, last resort) — LAST RESORT
    """
    console.print(f"[cyan]Searching for:[/cyan] [bold]{query}[/bold]")

    # ── 0. Serper API (If Key is Loaded) ─────────────────────────────────────
    if os.environ.get("SERPER_API_KEY"):
        urls = _search_serper_api(query, num_results)
        if urls:
            console.print(f"[green]Search complete (Serper): {len(urls)} URLs found[/green]")
            return urls
        console.print("[yellow]Serper API failed or returned 0 results. Falling back...[/yellow]")

    # ── 1. DuckDuckGo (fast, no browser) ─────────────────────────────────────
    urls = _search_duckduckgo_requests(query, num_results)
    if urls:
        console.print(f"[green]Search complete (DDG): {len(urls)} URLs found[/green]")
        return urls

    # ── 2. Google via Playwright (browser fallback) ───────────────────────────
    console.print("[yellow]DDG found 0 results. Falling back to Google browser search (slow)...[/yellow]")
    from playwright.sync_api import sync_playwright

    for browser_attempt in range(2):
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
                        ],
                        timeout=60000,
                    )
                except Exception as e:
                    console.print(f"[yellow]Browser launch failed (attempt {browser_attempt + 1}): {e}[/yellow]")
                    if browser_attempt < 1:
                        time.sleep(3)
                        continue
                    break

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
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
                """)
                page = context.new_page()

                # Try Google
                google_attempts = 0
                while google_attempts < 2 and not urls:
                    google_attempts += 1
                    console.print(f"[dim]Google attempt {google_attempts}/2...[/dim]")
                    urls = _search_google_playwright(query, num_results, page)
                    if urls:
                        console.print(f"[green]✓ Google found {len(urls)} results[/green]")
                        break
                    if google_attempts < 2:
                        time.sleep(3)

                # ── 3. Bing (last resort) ─────────────────────────────────────
                if not urls:
                    console.print("[yellow]⚠️  Google blocked/failed. Trying Bing as last resort...[/yellow]")
                    urls = _search_bing_playwright(query, num_results, page)
                    if urls:
                        console.print(f"[yellow]Bing found {len(urls)} results[/yellow]")

                browser.close()
                break

        except Exception as e:
            console.print(f"[red]Browser search attempt {browser_attempt + 1} failed: {e}[/red]")
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            if browser_attempt < 1:
                time.sleep(3)

    console.print(f"[green]Search complete: {len(urls)} URLs found[/green]")
    if not urls:
        console.print("[red]✗ WARNING: No URLs found from any search engine[/red]")
    return urls
