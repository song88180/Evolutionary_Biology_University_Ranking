import unittest
from rank_provisional import aggregate


class RankingTests(unittest.TestCase):
    def paper(self, doi='10.1/a', weight='10', status='ready'):
        return {'doi': doi, 'journal_impact_factor': weight, 'credit_status': status}

    def credit(self, key, doi='10.1/a', points='5', fraction='1/2', fallback=False):
        return {'doi': doi, 'institution_id': key, 'eligible_arwu_top1000': str(key != 'outside').lower(),
                'impact_factor_points_exact': points, 'fraction_exact': fraction,
                'credit_type': 'full' if fraction == '1' else 'fractional',
                'correspondence_evidence_status': 'explicit_openalex_correspondence_PROVISIONAL' if fallback else 'explicit_publisher_links_parsed'}

    def test_outside_share_not_redistributed_and_zero_is_observed_only(self):
        result = aggregate({'a': 'Alpha', 'b': 'Beta'}, [self.paper()], [self.credit('a'), self.credit('outside')])
        self.assertEqual(result[0]['total_impact_factor_score_exact'], '5')
        self.assertEqual(result[0]['fractional_credit_papers'], 1)
        self.assertEqual(result[1]['qualifying_papers'], 0)
        self.assertIn('OBSERVED_CREDITS_ONLY', result[1]['dataset_status'])

    def test_ties_and_fallback_source_breakdown(self):
        result = aggregate({'a': 'Alpha', 'b': 'Beta'}, [self.paper()], [self.credit('a', fallback=True), self.credit('b', fallback=True)])
        self.assertEqual([r['rank'] for r in result], [1, 1])
        self.assertEqual(result[0]['openalex_fallback_score_exact'], '5')
        self.assertEqual(result[0]['primary_correspondence_score_exact'], '0')

    def test_rejects_missing_denominator_and_duplicate_rows(self):
        for credits in [[self.credit('a')], [self.credit('a'), self.credit('a')]]:
            with self.assertRaises(ValueError):
                aggregate({'a': 'Alpha'}, [self.paper()], credits)

    def test_unresolved_paper_cannot_receive_points(self):
        with self.assertRaises(ValueError):
            aggregate({'a': 'Alpha'}, [self.paper(status='pending_institution_review')], [self.credit('a')])


if __name__ == '__main__':
    unittest.main()
