"""Scrape a list of TruePeopleSearch profile URLs into a CSV file.

Usage:
    export SCRAPEDO_TOKEN=your_token
    python scrape_profiles.py urls.txt profiles.csv

urls.txt holds one profile URL per line, copied from a manual search on
truepeoplesearch.com (https://www.truepeoplesearch.com/find/person/...).
"""

import csv
import sys

from truepeoplesearch_scraper import CSV_FIELDS, ScrapeError, TruePeopleSearchScraper


def main(url_file: str, out_file: str) -> None:
    with open(url_file, encoding="utf-8") as handle:
        urls = [line.strip() for line in handle if line.strip()]

    scraper = TruePeopleSearchScraper()  # reads SCRAPEDO_TOKEN
    with open(out_file, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for url in urls:
            try:
                person = scraper.get_profile(url)
            except (ScrapeError, ValueError) as exc:
                print(f"skipped {url}: {exc}")
                continue
            writer.writerow(person.to_row())
            print(f"{person.name}, {person.age}: {len(person.phones)} phones, {len(person.relatives)} relatives")


if __name__ == "__main__":
    main(*sys.argv[1:3])
