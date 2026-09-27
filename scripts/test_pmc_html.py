import unittest
from collect_pmc_html import parse


class PMCHTMLTests(unittest.TestCase):
    def fixture(self, note='Corresponding author: x@example.org', label='#'):
        return f'''<meta name="citation_doi" content="10.1/test">
        <section class="front-matter"><h1>Study</h1><div class="cg">
        <a aria-describedby="a1">A Author</a><div hidden id="a1"><div><sup>1</sup>University X</div></div><sup>1,</sup><sup>{label}</sup>
        <a aria-describedby="a2">B Author</a><div hidden id="a2"><div><sup>2</sup>University Y</div></div><sup>2,</sup><sup>*</sup></div>
        <div class="author-notes"><div class="fn" id="C1"><sup>#</sup>{note}</div>
        <div class="fn" id="E1"><sup>*</sup>These authors contributed equally</div></div></section>'''

    def test_correspondence_not_equal_contribution(self):
        result = parse(self.fixture(), {'doi': '10.1/test', 'pmcid': 'PMC1', 'title': 'Study'})
        self.assertEqual([a['name'] for a in result['corresponding_authors']], ['A Author'])
        self.assertEqual(result['corresponding_authors'][0]['affiliations'][0]['address'], 'University X')
        self.assertEqual(result['publisher_date'], '')

    def test_email_alone_insufficient(self):
        with self.assertRaises(ValueError):
            parse(self.fixture('x@example.org'), {'doi': '10.1/test'})

    def test_significance_and_abstract_both_retained(self):
        html = self.fixture() + '<section class="abstract">Significance: summary</section><section class="abstract">Abstract: main findings</section>'
        result = parse(html, {'doi': '10.1/test', 'pmcid': 'PMC1', 'title': 'Study'})
        self.assertIn('Significance: summary', result['abstract'])
        self.assertIn('Abstract: main findings', result['abstract'])

    def test_unlinked_note_fails(self):
        with self.assertRaises(ValueError):
            parse(self.fixture(label='*'), {'doi': '10.1/test'})


if __name__ == '__main__':
    unittest.main()
