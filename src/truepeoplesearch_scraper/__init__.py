"""Scrape TruePeopleSearch.com profile pages with Python."""

from .client import ScrapeError, TruePeopleSearchScraper
from .parser import CSV_FIELDS, Person, parse_profile

__all__ = [
    "CSV_FIELDS",
    "Person",
    "ScrapeError",
    "TruePeopleSearchScraper",
    "parse_profile",
]

__version__ = "0.1.0"
