import unittest

from collect_oup_articles import parse


def card(name, more=False, correspondence=True, affiliation=True):
    return (f'<div class="al-author-name{"-more" if more else ""} js-flyout-wrap">'
            f'<a class="linked-name">{name}</a>'
            + ('<div class="info-card-affilitation"><div class="aff">University A</div></div>' if affiliation else '')
            + ('<div class="info-author-correspondence">Corresponding author</div>' if correspondence else '') + '</div>')


class OUPTests(unittest.TestCase):
    def html(self, cards):
        return ('<h1 class="article-title-main">Test article</h1>'
                '<div class="ww-citation-primary"><a href="https://doi.org/10.1093/molbev/test">DOI</a></div>'
                '<div class="citation-label">Published:</div><div class="citation-date">24 September 2026</div>'
                '<span>Accepted manuscript</span>' + cards)

    def test_hidden_authors_and_version(self):
        result = parse(self.html(card('First', correspondence=False) + card('Second', more=True)), '10.1093/molbev/test', 'publisher')
        self.assertEqual([a['name'] for a in result['corresponding_authors']], ['Second'])
        self.assertEqual(result['publisher_date'], '2026-09-24')
        self.assertEqual(result['publication_version'], 'accepted_manuscript')

    def test_missing_affiliation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            parse(self.html(card('Name', affiliation=False)), '10.1093/molbev/test', 'publisher')

    def test_mismatched_doi_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DOI mismatch'):
            parse(self.html(card('Name')), '10.1093/molbev/different', 'publisher')


if __name__ == '__main__':
    unittest.main()
