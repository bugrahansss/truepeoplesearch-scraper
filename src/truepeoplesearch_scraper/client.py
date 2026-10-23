"""Fetch TruePeopleSearch pages through the Scrape.do API.

TruePeopleSearch has two defenses a plain HTTP client cannot pass:

* It is geofenced to the United States. Requests from other countries are cut
  off before the page loads.
* It sits behind Cloudflare bot protection, which challenges or blocks
  library and datacenter traffic.

Sending the request through Scrape.do with ``geoCode=us`` and ``super=true``
routes it through a US residential IP, which clears both.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import requests

from .parser import Person, parse_profile

API_URL = "https://api.scrape.do/"
TOKEN_ENV = "SCRAPEDO_TOKEN"


class ScrapeError(RuntimeError):
    """Raised when a page cannot be fetched."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TruePeopleSearchScraper:
    """Fetch and parse TruePeopleSearch profile pages.

    >>> scraper = TruePeopleSearchScraper(token="YOUR_SCRAPEDO_TOKEN")
    >>> person = scraper.get_profile("https://www.truepeoplesearch.com/find/person/...")
    >>> person.name, person.phone
    """

    def __init__(
        self,
        token: Optional[str] = None,
        timeout: float = 90.0,
        retries: int = 2,
        session: Optional[requests.Session] = None,
    ):
        self.token = token or os.environ.get(TOKEN_ENV, "")
        if not self.token:
            raise ValueError(
                f"A Scrape.do API token is required. Pass token=... or set {TOKEN_ENV}."
            )
        self.timeout = timeout
        self.retries = max(0, retries)
        self.session = session or requests.Session()

    def fetch(self, url: str) -> str:
        """Return the raw HTML of ``url``, fetched from a US residential IP."""
        params = {"token": self.token, "url": url, "super": "true", "geoCode": "us"}
        last_error: Optional[ScrapeError] = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(API_URL, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = ScrapeError(f"Request failed: {exc}")
            else:
                if response.status_code == 200:
                    return response.text
                last_error = ScrapeError(
                    f"Request for {url} failed with status {response.status_code}",
                    status_code=response.status_code,
                )
                # Client errors (bad token, bad URL, not found) will not fix themselves
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    break
            if attempt < self.retries:
                time.sleep(2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def get_profile(self, url: str) -> Person:
        """Fetch one profile page and parse it."""
        return parse_profile(self.fetch(url), url=url)
