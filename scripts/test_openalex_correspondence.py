"""Offline regression checks for correspondence evidence handling."""
import json
import unittest
from unittest.mock import patch

import requests

from check_openalex_correspondence import RATE_LIMITED, check, compare_publisher, normalize_doi, parse_work


class CorrespondenceTests(unittest.TestCase):
    def tearDown(self):
        RATE_LIMITED.clear()

    def test_doi_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_work({"doi": "https://doi.org/10.1/other"}, "10.1/paper")

    def test_no_last_author_inference(self):
        work = {"doi": "https://doi.org/10.1/paper", "authorships": [
            {"raw_author_name": "Last Author", "author_position": "last", "is_corresponding": False}]}
        result = parse_work(work, "10.1/paper")
        self.assertEqual(result["status"], "no_corresponding_author_flag")
        self.assertEqual(json.loads(result["corresponding_authors_json"]), [])

    def test_raw_affiliations_not_replaced_by_institution_labels(self):
        work = {"doi": "https://doi.org/10.1/paper", "authorships": [
            {"raw_author_name": "A Author", "is_corresponding": True,
             "raw_affiliation_strings": ["University A and Institute B"],
             "institutions": [{"display_name": "Institute B"}]}]}
        result = parse_work(work, "10.1/paper")
        author = json.loads(result["corresponding_authors_json"])[0]
        self.assertEqual(author["affiliations"], ["University A and Institute B"])
        self.assertEqual(author["institutions"], ["Institute B"])

    def test_name_match_does_not_validate_missing_affiliation(self):
        publisher = [{"name": "A. Author", "affiliations": [{"address": "University A"}, {"address": "University B"}]}]
        candidate = [{"name": "A Author", "affiliations": ["University A"]}]
        self.assertEqual(compare_publisher(candidate, publisher), "author_names_agree_affiliation_text_differs")

    def test_complete_text_agreement(self):
        publisher = [{"name": "A. Author", "affiliations": [{"address": "Université A"}]}]
        candidate = [{"name": "A Author", "affiliations": ["Universite A"]}]
        self.assertEqual(compare_publisher(candidate, publisher), "names_and_raw_affiliations_agree")

    def test_author_cap_flag(self):
        result = parse_work({"doi": "https://doi.org/10.1/paper", "authorships": [{}] * 100}, "10.1/paper")
        self.assertEqual(result["possible_authorship_truncation"], "true")

    def test_doi_normalization(self):
        self.assertEqual(normalize_doi(" HTTPS://DOI.ORG/10.1/Paper "), "10.1/paper")

    @patch("check_openalex_correspondence.fetch")
    def test_cached_only_never_fetches_missing_record(self, fetch):
        result = check({"doi": "10.1/uncached-test"}, cached_only=True)
        self.assertEqual(result["status"], "not_yet_queried")
        fetch.assert_not_called()

    @patch("check_openalex_correspondence.fetch")
    def test_rate_limit_stops_following_requests(self, fetch):
        response = requests.Response()
        response.status_code = 429
        response.headers["Retry-After"] = "100"
        fetch.side_effect = requests.HTTPError(response=response)
        first = check({"doi": "10.1/uncached-test"})
        second = check({"doi": "10.1/another-uncached-test"})
        self.assertEqual(first["status"], "rate_limited")
        self.assertEqual(first["retry_after_seconds"], "100")
        self.assertEqual(second["status"], "deferred_rate_limit")
        self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
