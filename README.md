# truepeoplesearch-scraper

[![PyPI](https://img.shields.io/pypi/v/truepeoplesearch-scraper)](https://pypi.org/project/truepeoplesearch-scraper/)
[![Python](https://img.shields.io/pypi/pyversions/truepeoplesearch-scraper)](https://pypi.org/project/truepeoplesearch-scraper/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Python scraper for [TruePeopleSearch.com](https://www.truepeoplesearch.com) person profile pages. One call returns the name, age, current address with ZIP code, every listed phone number and email, aliases and relatives, as a Python object, JSON or CSV.

```bash
pip install truepeoplesearch-scraper
```

## Why a plain request fails

TruePeopleSearch has no public API, and it has two defenses that stop `requests`, `httpx` and most headless browsers before the page loads:

| Defense | What happens |
|---|---|
| **US-only geofence** | From a non-US IP the connection is cut off. No error page, no content. |
| **Cloudflare** | Library and datacenter traffic gets JavaScript challenges, CAPTCHAs, and rate limiting that escalates with request frequency. |

This package sends each request through the [Scrape.do](https://scrape.do) API with two parameters:

- `geoCode=us` keeps the exit IP in the United States
- `super=true` uses a residential IP instead of a datacenter one

That clears both defenses in a single request: no proxy rotation, no header tuning, no browser. You need a Scrape.do API token; the free plan includes 1,000 credits a month.

## Quick start

```python
from truepeoplesearch_scraper import TruePeopleSearchScraper

scraper = TruePeopleSearchScraper(token="YOUR_SCRAPEDO_TOKEN")  # or set SCRAPEDO_TOKEN
person = scraper.get_profile("https://www.truepeoplesearch.com/find/person/<profile-id>")

print(person.name, person.age)
print(person.address, person.city, person.state, person.zip_code)
print(person.phone)      # first listed phone
print(person.phones)     # all of them
print(person.emails, person.aliases, person.relatives)
```

Get the profile URL from a normal search on truepeoplesearch.com. The scraper reads profile pages, not search result pages.

### Command line

```bash
export SCRAPEDO_TOKEN=your_token

# one profile, JSON to stdout
truepeoplesearch-scraper "https://www.truepeoplesearch.com/find/person/<profile-id>"

# many profiles, one URL per line, CSV file
truepeoplesearch-scraper --input urls.txt --format csv --output profiles.csv
```

### Output

Run on the fictional test profile in [`tests/fixtures`](tests/fixtures/profile_jane_doe.html):

```json
{
  "name": "Jane Doe",
  "first_name": "Jane",
  "last_name": "Doe",
  "age": 23,
  "address": "2912 Northern Ave WE",
  "city": "Washington",
  "state": "DC",
  "zip_code": "20001",
  "phones": ["(202) 555-5555", "(202) 555-0147", "(202) 555-0199"],
  "emails": ["janedoe@example.com", "jane.m.doe@example.com"],
  "aliases": ["Jane Marie Doe", "Jane D Smith", "Jane M Johnson"],
  "relatives": ["John Doe", "Mary Doe", "Robert Smith", "Emily Doe", "Thomas Doe"],
  "url": "https://www.truepeoplesearch.com/find/person/jane-doe"
}
```

In CSV output, list fields are joined with ` | `, so every value fits in one cell.

## Fields

| Field | Source on the page |
|---|---|
| `first_name`, `last_name`, `age` | `data-fn`, `data-ln`, `data-age` attributes on `div#personDetails` |
| `address`, `city`, `state`, `zip_code` | JSON-LD `address`, falling back to the `itemprop` spans in the address link |
| `phones` | JSON-LD `telephone` array, falling back to `span[itemprop=telephone]` |
| `emails` | JSON-LD `email` array |
| `aliases` | JSON-LD `alternateName` array |
| `relatives` | JSON-LD `relatedTo` array (`name` of each person) |

## How the parser works

Every profile page embeds a `<script type="application/ld+json">` block of type `ProfilePage`. Its `mainEntity` is the person, with all phones, emails, aliases and relatives in clean arrays, and the full address including ZIP code. That block holds more than the visible HTML: profiles often list several phones and emails, and the JSON-LD keeps full middle names that the page abbreviates.

The parser reads the name and age from the `data-*` attributes, reads the JSON-LD, and uses the visible `itemprop` spans only where the JSON-LD has no value. Selectors are tied to the page's data attributes and schema.org markup, not to CSS class names, so a restyle is less likely to break them.

You can also parse HTML you already have:

```python
from truepeoplesearch_scraper import parse_profile

person = parse_profile(html, url=profile_url)
```

`parse_profile` raises `ValueError` when the page has no profile data, which usually means you passed a challenge page or a search page.

## Limits

- **Profile pages only.** Search and address pages are not parsed.
- **Rate limits.** Cloudflare escalates when requests come too fast. Scrape.do rotates residential IPs automatically, but spacing requests out still helps.
- **Layout changes.** If TruePeopleSearch changes its markup, `parse_profile` may return empty fields. Open an issue with the field that broke.
- **Errors.** Non-200 responses raise `ScrapeError` with the status code. Server errors and 429s are retried twice; client errors are not.

## Responsible use

This data describes real people. Do not use it to make decisions about employment, housing, credit or insurance: in the US those uses are regulated by the Fair Credit Reporting Act. Honor opt-out requests, follow the privacy laws that apply to you, and follow TruePeopleSearch's terms. This is not legal advice.

## Development

```bash
git clone https://github.com/bugrahansss/truepeoplesearch-scraper
cd truepeoplesearch-scraper
pip install -e .
python -m unittest discover -s tests -v
```

The tests run offline against a fictional fixture page.

## License

MIT

---

Source: [TruePeopleSearch.com Scraping: Extract Data Without Blocks](https://scrape.do/blog/true-people-search-scraping/)
