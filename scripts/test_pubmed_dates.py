import unittest
from collect_pubmed_dates import electronic_dates


class PubMedDateTests(unittest.TestCase):
    def test_only_explicit_electronic_date(self):
        xml = '''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
        <Journal><JournalIssue><PubDate><Year>2026</Year><Month>5</Month><Day>1</Day></PubDate></JournalIssue></Journal>
        <ArticleDate DateType="Electronic"><Year>2026</Year><Month>03</Month><Day>20</Day></ArticleDate>
        </Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/Test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>'''
        self.assertEqual(electronic_dates(xml)['10.1/test']['online_date'], '2026-03-20')
        self.assertEqual(electronic_dates(xml.replace('DateType="Electronic"', 'DateType="Print"')), {})
