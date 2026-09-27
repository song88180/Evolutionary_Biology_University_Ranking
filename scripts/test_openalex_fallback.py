import copy
import unittest

from prepare_openalex_fallback import provisional_correspondence


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.work = {'doi': 'https://doi.org/10.1/paper', 'id': 'https://openalex.org/W1',
                     'corresponding_author_ids': ['A1'],
                     'authorships': [{'author': {'id': 'A1'}, 'raw_author_name': 'Author A',
                                     'is_corresponding': True,
                                     'raw_affiliation_strings': ['University A and Institute B']},
                                    {'raw_author_name': 'Author B', 'is_corresponding': False,
                                     'raw_affiliation_strings': ['University C']}]}

    def test_explicit_only_and_preserves_joint_raw_affiliation(self):
        record = provisional_correspondence(self.work, '10.1/paper')
        self.assertEqual(len(record['corresponding_authors']), 1)
        self.assertEqual(record['corresponding_authors'][0]['affiliations'][0]['address'], 'University A and Institute B')
        self.assertIn('PROVISIONAL', record['extraction_status'])

    def test_never_overrides_primary(self):
        for primary in [{'extraction_status': 'explicit_publisher_links_parsed'},
                        {'extraction_status': 'explicit_repository_links_parsed'},
                        {'corresponding_authors': [{'name': 'Unresolved primary author'}]}]:
            with self.assertRaises(ValueError):
                provisional_correspondence(self.work, '10.1/paper', primary)

    def test_rejects_incomplete_and_mismatched_records(self):
        variants = []
        for field, value in [('doi', 'https://doi.org/10.1/other'),
                             ('authorships', self.work['authorships'] * 50),
                             ('corresponding_author_ids', ['A2'])]:
            candidate = copy.deepcopy(self.work)
            candidate[field] = value
            variants.append(candidate)
        candidate = copy.deepcopy(self.work)
        candidate['authorships'][0]['is_corresponding'] = False
        variants.append(candidate)
        candidate = copy.deepcopy(self.work)
        candidate['authorships'][0]['raw_affiliation_strings'] = []
        variants.append(candidate)
        for work in variants:
            with self.assertRaises(ValueError):
                provisional_correspondence(work, '10.1/paper')

    def test_does_not_mutate_input(self):
        self.work['authorships'][0]['affiliations'] = [{'raw_affiliation_string': 'Institute D'}]
        original = copy.deepcopy(self.work)
        result = provisional_correspondence(self.work, '10.1/paper')
        self.assertEqual(self.work, original)
        self.assertEqual(len(result['corresponding_authors'][0]['affiliations']), 2)


if __name__ == '__main__':
    unittest.main()
