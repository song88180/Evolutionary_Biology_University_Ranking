import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import review_records


class ReviewEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data/articles').mkdir(parents=True)
        (self.root / 'data/sources').mkdir()
        self.doi = '10.1073/pnas.test'
        self.url = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC1/'
        self.cache = self.root / 'data/sources' / (hashlib.sha256(self.url.encode()).hexdigest() + '.body')
        with (self.root / 'data/screening_audit_INCOMPLETE.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['doi', 'pmcid'])
            writer.writeheader()
            writer.writerow({'doi': self.doi, 'pmcid': 'PMC1'})
        self.patch = patch.object(review_records, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_old_pmc_record_uses_all_primary_abstracts(self):
        (self.root / 'data/articles/pnas.test.json').write_text(json.dumps({
            'source_url': self.url, 'title': 'Study', 'abstract': 'Significance only'}))
        self.cache.write_text('<section class="abstract">Significance</section>'
                              '<section class="abstract">Complete scientific abstract</section>')
        result = review_records.abstracts([self.doi])[0]
        self.assertEqual(result['abstract'], 'Significance\nComplete scientific abstract')

    def test_text_review_does_not_require_correspondence_extraction(self):
        self.cache.write_text('<meta name="citation_doi" content="10.1073/pnas.test">'
                              '<div class="main-article-body"><section><h2>Discussion</h2>'
                              '<p>Evolutionary result.</p></section></div>')
        result = review_records.article_evidence(self.doi, 'evolution', 2, section='Discussion')
        self.assertEqual(result['selected_paragraphs'][0]['text'], 'Evolutionary result.')
        self.assertFalse((self.root / 'data/articles/pnas.test.json').exists())

    def test_unparsed_cache_requires_matching_doi(self):
        self.cache.write_text('<meta name="citation_doi" content="10.1073/wrong">'
                              '<div class="main-article-body"><p>Evolutionary result.</p></div>')
        result = review_records.article_evidence(self.doi, 'evolution', 2)
        self.assertIn('does not verify', result['error'])

    def test_jats_text_available_without_correspondence(self):
        url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML'
        cache = self.root / 'data/sources' / (hashlib.sha256(url.encode()).hexdigest() + '.body')
        cache.write_text('<article><front><article-meta><article-id pub-id-type="doi">'
                         '10.1073/pnas.test</article-id></article-meta></front>'
                         '<body><p>Original evolutionary analysis.</p></body></article>')
        result = review_records.article_evidence(self.doi, 'evolution', 2)
        self.assertEqual(result['source'], url)
        self.assertEqual(result['matching_paragraph_count'], 1)


if __name__ == '__main__':
    unittest.main()
