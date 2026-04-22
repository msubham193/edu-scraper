"""
extractor.py
------------
Extracts name, emails, and phone numbers from raw HTML/text.
Uses regex + phonenumbers library for robust parsing.
"""

import re
import phonenumbers
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# ─── Email Regex ───────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}"
)

# ─── Raw Indian phone patterns (fallback) ──────────────────────────────────────
# Matches:  +91-XXXXXXXXXX  /  0XX-XXXXXXX  /  10-digit mobile  /  landline
PHONE_REGEX = re.compile(
    r"(?:"
    r"\+91[\s\-]?\d{10}"           # +91 mobile
    r"|\+91[\s\-]?\d{4}[\s\-]?\d{6}"  # +91 landline
    r"|0\d{2,4}[\s\-]?\d{6,8}"    # 0XX landlines
    r"|[6-9]\d{9}"                  # 10-digit Indian mobile
    r")"
)

# Noise emails to discard
JUNK_EMAIL_DOMAINS = {"example.com", "domain.com", "email.com", "test.com",
                       "yoursite.com", "sentry.io", "wixpress.com", "squarespace.com"}


def extract_emails(text: str) -> list[str]:
    """Return deduplicated list of valid emails found in text."""
    found = EMAIL_REGEX.findall(text)
    cleaned = []
    seen = set()
    for email in found:
        email = email.lower().strip(".")
        domain = email.split("@")[-1]
        if domain in JUNK_EMAIL_DOMAINS:
            continue
        if email not in seen:
            seen.add(email)
            cleaned.append(email)
    return cleaned


def extract_phones(text: str, region: str = "IN") -> list[str]:
    """
    Extracts phone numbers from text using two strategies:
    1. phonenumbers library (structured parsing)
    2. Regex fallback for raw Indian number formats
    """
    found = set()

    # Strategy 1: phonenumbers library
    for match in phonenumbers.PhoneNumberMatcher(text, region):
        num = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        found.add(num)

    # Strategy 2: Regex fallback
    for m in PHONE_REGEX.finditer(text):
        raw = m.group().strip()
        # Normalize: remove spaces/dashes
        digits = re.sub(r"[\s\-]", "", raw)
        try:
            parsed = phonenumbers.parse(digits, region)
            if phonenumbers.is_valid_number(parsed):
                fmt = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                found.add(fmt)
        except Exception:
            found.add(raw)  # store as-is if parse fails

    return list(found)


def extract_mailto_emails(soup: BeautifulSoup) -> list[str]:
    """Extract emails encoded in mailto: href attributes."""
    emails = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip().lower()
            if email and "@" in email:
                emails.append(email)
    return emails


def extract_tel_phones(soup: BeautifulSoup, region: str = "IN") -> list[str]:
    """Extract phone numbers encoded in tel: href attributes."""
    phones = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("tel:"):
            raw = href.replace("tel:", "").strip()
            digits = re.sub(r"[\s\-\(\)]", "", raw)
            try:
                parsed = phonenumbers.parse(digits, region)
                if phonenumbers.is_valid_number(parsed):
                    fmt = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    phones.append(fmt)
            except Exception:
                phones.append(raw)
    return phones


def extract_name(soup: BeautifulSoup, url: str) -> str:
    """
    Extract organization name using multiple strategies:
    1. og:site_name meta tag
    2. og:title meta tag
    3. <title> tag (cleaned)
    4. First <h1>
    5. Domain name fallback
    """
    # og:site_name
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        return og_site["content"].strip()

    # og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # <title>
    title = soup.find("title")
    if title and title.text:
        t = title.text.strip()
        # Remove common suffixes
        for sep in ["|", "-", "–", "—", ":", ","]:
            if sep in t:
                t = t.split(sep)[0].strip()
        if t:
            return t

    # First <h1>
    h1 = soup.find("h1")
    if h1 and h1.text.strip():
        return h1.text.strip()

    # Domain fallback
    domain = urlparse(url).netloc.replace("www.", "").split(".")[0]
    return domain.replace("-", " ").replace("_", " ").title()


def extract_all(html: str, url: str) -> dict:
    """
    Master extraction function.
    Returns dict with: name, emails, phones, url.
    Returns a flagged empty result if the page is a search engine page.
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)

    # Guard: skip if we accidentally scraped a search engine page
    page_title = (soup.find("title") or {}).get_text().strip().lower() if soup.find("title") else ""
    from urllib.parse import urlparse as _urlparse
    _domain = _urlparse(url).netloc.lower().replace("www.", "")
    _search_engines = ["bing.com", "google.com", "yahoo.com", "microsoft.com"]
    if any(se in _domain for se in _search_engines):
        return {"name": "", "emails": [], "phones": [], "url": url, "_skip": True}

    name = extract_name(soup, url)

    # Combine mailto + regex emails
    emails = list(set(
        extract_mailto_emails(soup) + extract_emails(text)
    ))

    # Combine tel + regex phones
    phones = list(set(
        extract_tel_phones(soup) + extract_phones(text)
    ))

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "url": url
    }
