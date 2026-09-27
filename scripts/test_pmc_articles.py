import unittest
import xml.etree.ElementTree as ET
from collect_pmc_articles import parse_article, affiliation_text, is_contribution_note


class RepositoryCorrespondenceTests(unittest.TestCase):
    def test_affiliation_labels_are_not_part_of_address(self):
        self.assertEqual(affiliation_text(ET.fromstring('<aff><sup>a</sup><institution>University A</institution>, City</aff>')), 'University A, City')
        self.assertEqual(affiliation_text(ET.fromstring('<aff><label>1</label>University B</aff>')), 'University B')
        self.assertTrue(is_contribution_note('Lead contact'))
        self.assertTrue(is_contribution_note('These authors contributed equally.'))
        self.assertTrue(is_contribution_note('Senior authors'))
        self.assertFalse(is_contribution_note('Lead Contact Research Institute, University A'))

    def test_shared_correspondence_and_all_affiliations(self):
        xml = '''<article article-type="research-article"><front><article-meta>
        <article-id pub-id-type="doi">10.1/test</article-id>
        <pub-date pub-type="epub"><year>2025</year><month>9</month><day>24</day></pub-date>
        <contrib-group><contrib contrib-type="author"><name><given-names>A</given-names><surname>B</surname></name>
        <xref ref-type="corresp" rid="c1"/><xref ref-type="aff" rid="a1 a2"/></contrib>
        <contrib contrib-type="author"><name><given-names>C</given-names><surname>D</surname></name>
        <xref ref-type="aff" rid="a3"/></contrib></contrib-group>
        <aff id="a1"><label>1</label>University A</aff><aff id="a2">Institute B</aff><aff id="a3">University C</aff>
        <author-notes><corresp id="c1">Correspondence to A B</corresp></author-notes>
        </article-meta></front></article>'''
        result = parse_article(xml, {"doi": "10.1/test", "pmcid": "PMC1"})
        self.assertEqual(result["publisher_date"], "2025-09-24")
        self.assertEqual(result["extraction_status"], "explicit_repository_links_parsed")
        self.assertEqual(len(result["corresponding_authors"]), 1)
        self.assertEqual([a["address"] for a in result["corresponding_authors"][0]["affiliations"]], ["University A", "Institute B"])
        unmatched = xml.replace('</author-notes>', '<corresp id="c2">Another correspondent</corresp></author-notes>')
        self.assertEqual(parse_article(unmatched, {"doi": "10.1/test", "pmcid": "PMC1"})["extraction_status"], "repository_links_need_review")

    def test_inline_affiliations_and_correspondence_footnote(self):
        xml = '''<article><front><article-meta><article-id pub-id-type="doi">10.1/test</article-id>
        <pub-date pub-type="epub"><year>2026</year><month>9</month><day>24</day></pub-date>
        <contrib-group><contrib><name><given-names>A</given-names><surname>B</surname></name>
        <aff>University A</aff><aff>Institute B</aff><xref ref-type="author-notes" rid="note1"/></contrib></contrib-group>
        <author-notes><fn id="note1"><p><bold>Corresponding author:</bold> E-mail: example@example.org</p></fn></author-notes>
        </article-meta></front></article>'''
        result = parse_article(xml, {"doi": "10.1/test", "pmcid": "PMC1"})
        self.assertEqual(result["extraction_status"], "explicit_repository_links_parsed")
        self.assertEqual(len(result["corresponding_authors"][0]["affiliations"]), 2)


if __name__ == "__main__":
    unittest.main()
