import csv
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from truepeoplesearch_scraper import CSV_FIELDS, ScrapeError, TruePeopleSearchScraper, parse_profile
from truepeoplesearch_scraper import cli

FIXTURE = (Path(__file__).parent / "fixtures" / "profile_jane_doe.html").read_text(encoding="utf-8")
URL = "https://www.truepeoplesearch.com/find/person/jane-doe"

HTML_ONLY = """
<div id="personDetails" data-fn="John" data-ln="Roe" data-age="41"></div>
<a data-link-to-more="address"><span itemprop="streetAddress">10 Main St</span>
<span itemprop="addressLocality">Springfield</span><span itemprop="addressRegion">IL</span></a>
<a data-link-to-more="phone"><span itemprop="telephone">(217) 555-0100</span></a>
"""


class ParseProfileTest(unittest.TestCase):
    def test_full_profile(self):
        p = parse_profile(FIXTURE, url=URL)
        self.assertEqual(p.name, "Jane Doe")
        self.assertEqual((p.first_name, p.last_name, p.age), ("Jane", "Doe", 23))
        self.assertEqual((p.address, p.city, p.state, p.zip_code), ("2912 Northern Ave WE", "Washington", "DC", "20001"))
        self.assertEqual(p.phone, "(202) 555-5555")
        self.assertEqual(len(p.phones), 3)
        self.assertEqual(p.email, "janedoe@example.com")
        self.assertEqual(p.aliases, ["Jane Marie Doe", "Jane D Smith", "Jane M Johnson"])
        self.assertEqual(p.relatives[:2], ["John Doe", "Mary Doe"])
        self.assertEqual(len(p.relatives), 5)
        self.assertEqual(p.url, URL)

    def test_html_only_fallback(self):
        p = parse_profile(HTML_ONLY)
        self.assertEqual((p.name, p.age), ("John Roe", 41))
        self.assertEqual((p.address, p.city, p.state, p.zip_code), ("10 Main St", "Springfield", "IL", ""))
        self.assertEqual(p.phones, ["(217) 555-0100"])
        self.assertEqual((p.emails, p.relatives), ([], []))

    def test_not_a_profile(self):
        with self.assertRaises(ValueError):
            parse_profile("<html><body>Just a moment...</body></html>")

    def test_csv_row(self):
        row = parse_profile(FIXTURE).to_row()
        self.assertEqual(list(row), CSV_FIELDS)
        self.assertEqual(row["relatives"], "John Doe | Mary Doe | Robert Smith | Emily Doe | Thomas Doe")


class ClientTest(unittest.TestCase):
    def _response(self, status, text=""):
        r = mock.Mock()
        r.status_code, r.text = status, text
        return r

    def test_requires_token(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                TruePeopleSearchScraper()

    def test_request_parameters(self):
        session = mock.Mock()
        session.get.return_value = self._response(200, FIXTURE)
        person = TruePeopleSearchScraper(token="T", session=session).get_profile(URL)
        _, kwargs = session.get.call_args
        self.assertEqual(kwargs["params"], {"token": "T", "url": URL, "super": "true", "geoCode": "us"})
        self.assertEqual(person.name, "Jane Doe")

    def test_client_error_is_not_retried(self):
        session = mock.Mock()
        session.get.return_value = self._response(401)
        with self.assertRaises(ScrapeError) as ctx:
            TruePeopleSearchScraper(token="T", session=session, retries=3).fetch(URL)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(session.get.call_count, 1)

    @mock.patch("truepeoplesearch_scraper.client.time.sleep")
    def test_server_error_is_retried(self, _sleep):
        session = mock.Mock()
        session.get.side_effect = [self._response(502), self._response(200, FIXTURE)]
        html = TruePeopleSearchScraper(token="T", session=session, retries=2).fetch(URL)
        self.assertIn("personDetails", html)
        self.assertEqual(session.get.call_count, 2)


class CliTest(unittest.TestCase):
    @mock.patch("truepeoplesearch_scraper.client.TruePeopleSearchScraper.fetch", return_value=FIXTURE)
    def test_json_and_csv_output(self, _fetch):
        for fmt in ("json", "csv"):
            out = io.StringIO()
            with mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
                code = cli.main([URL, "--token", "T", "--format", fmt])
            self.assertEqual(code, 0)
            if fmt == "json":
                self.assertEqual(json.loads(out.getvalue())[0]["zip_code"], "20001")
            else:
                rows = list(csv.DictReader(io.StringIO(out.getvalue())))
                self.assertEqual(rows[0]["name"], "Jane Doe")


if __name__ == "__main__":
    unittest.main()
