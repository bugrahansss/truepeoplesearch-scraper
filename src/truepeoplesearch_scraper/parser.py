"""Parse a TruePeopleSearch person profile page into structured data.

Two sources on the page are used:

1. HTML attributes. The ``#personDetails`` block carries the first name, last
   name and age as ``data-fn``, ``data-ln`` and ``data-age``. The current
   address and phone sit in anchors marked with ``data-link-to-more`` and
   spans with schema.org ``itemprop`` names.
2. JSON-LD. A ``<script type="application/ld+json">`` block of type
   ``ProfilePage`` holds the person as ``mainEntity``: every phone, email,
   alias and relative, plus the full address with ZIP code.

JSON-LD is preferred where both exist, because it holds more values and keeps
full middle names. The HTML attributes fill any gaps.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup


@dataclass
class Person:
    """One TruePeopleSearch profile."""

    name: str = ""
    first_name: str = ""
    last_name: str = ""
    age: Optional[int] = None
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phones: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    relatives: List[str] = field(default_factory=list)
    url: str = ""

    @property
    def phone(self) -> str:
        """The first listed phone, usually the most recent one."""
        return self.phones[0] if self.phones else ""

    @property
    def email(self) -> str:
        """The first listed email, usually the most recent one."""
        return self.emails[0] if self.emails else ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_row(self, separator: str = " | ") -> Dict[str, Any]:
        """A flat dict for CSV output; list fields are joined with ``separator``."""
        row = self.to_dict()
        for key in ("phones", "emails", "aliases", "relatives"):
            row[key] = separator.join(row[key])
        return row


CSV_FIELDS = [
    "name",
    "first_name",
    "last_name",
    "age",
    "address",
    "city",
    "state",
    "zip_code",
    "phones",
    "emails",
    "aliases",
    "relatives",
    "url",
]


def _text(element) -> str:
    return " ".join(element.get_text().split()) if element is not None else ""


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_strings(values: Iterable[Any]) -> List[str]:
    seen = set()
    out = []
    for value in values:
        if not isinstance(value, str):
            continue
        value = " ".join(value.split())
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _iter_jsonld(soup: BeautifulSoup) -> Iterable[Dict[str, Any]]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _as_list(data):
            if not isinstance(item, dict):
                continue
            yield item
            for node in _as_list(item.get("@graph")):
                if isinstance(node, dict):
                    yield node


def find_profile_jsonld(soup: BeautifulSoup) -> Dict[str, Any]:
    """Return the person (``mainEntity``) from the ProfilePage JSON-LD block, or {}."""
    for item in _iter_jsonld(soup):
        if item.get("@type") == "ProfilePage":
            entity = item.get("mainEntity")
            if isinstance(entity, list):
                entity = next((e for e in entity if isinstance(e, dict)), None)
            if isinstance(entity, dict):
                return entity
    return {}


def parse_profile(html: str, url: str = "") -> Person:
    """Parse the HTML of one TruePeopleSearch profile page.

    Raises ``ValueError`` if the page has neither the ``#personDetails`` block
    nor a ProfilePage JSON-LD block, which usually means a block page or a
    search page was passed in instead of a profile.
    """
    soup = BeautifulSoup(html, "html.parser")
    person = Person(url=url)

    details = soup.find("div", id="personDetails")
    entity = find_profile_jsonld(soup)
    if details is None and not entity:
        raise ValueError(
            "No profile data found. Expected a TruePeopleSearch person profile page "
            "(div#personDetails or a ProfilePage JSON-LD block)."
        )

    # 1. Name and age from data attributes
    if details is not None:
        person.first_name = (details.get("data-fn") or "").strip()
        person.last_name = (details.get("data-ln") or "").strip()
        person.age = _to_int(details.get("data-age"))
        person.name = " ".join(p for p in (person.first_name, person.last_name) if p)

    # 2. Current address and phone from the visible HTML
    addr = soup.find("a", attrs={"data-link-to-more": "address"})
    if addr is not None:
        person.address = _text(addr.find("span", itemprop="streetAddress"))
        person.city = _text(addr.find("span", itemprop="addressLocality"))
        person.state = _text(addr.find("span", itemprop="addressRegion"))
        person.zip_code = _text(addr.find("span", itemprop="postalCode"))

    html_phones = [
        _text(a.find("span", itemprop="telephone"))
        for a in soup.find_all("a", attrs={"data-link-to-more": "phone"})
    ]

    # 3. JSON-LD fills in everything else and wins where both exist
    if entity:
        if not person.name:
            person.name = " ".join(str(entity.get("name", "")).split())
        address = entity.get("address")
        if isinstance(address, list):
            address = next((a for a in address if isinstance(a, dict)), {})
        if isinstance(address, dict):
            person.address = " ".join(str(address.get("streetAddress", "")).split()) or person.address
            person.city = " ".join(str(address.get("addressLocality", "")).split()) or person.city
            person.state = " ".join(str(address.get("addressRegion", "")).split()) or person.state
            person.zip_code = " ".join(str(address.get("postalCode", "")).split()) or person.zip_code
        person.phones = _clean_strings(_as_list(entity.get("telephone")))
        person.emails = _clean_strings(_as_list(entity.get("email")))
        person.aliases = _clean_strings(_as_list(entity.get("alternateName")))
        person.relatives = _clean_strings(
            rel.get("name") if isinstance(rel, dict) else rel
            for rel in _as_list(entity.get("relatedTo"))
        )

    if not person.phones:
        person.phones = _clean_strings(html_phones)

    return person
