"""Rank observed, completely allocated credits, explicitly not an exhaustive result.

All 1,000 pool institutions are retained. Zero observed credit is not evidence
of zero eligible output while scientific screening or evidence review is open.
Equal exact scores receive the same competition rank; name ordering only makes
display reproducible and does not break a score tie.
"""
from collections import defaultdict
import csv
from fractions import Fraction
import json

from study_config import ROOT, START, END, screening_decisions
from export_reviewed import save


def aggregate(pool, papers, credits):
    by_doi = defaultdict(list)
    seen = set()
    for credit in credits:
        key = (credit['doi'], credit['institution_id'])
        if key in seen:
            raise ValueError('Duplicate credit row')
        seen.add(key)
        by_doi[credit['doi']].append(credit)
    values = {key: {'score': Fraction(), 'primary': Fraction(), 'fallback': Fraction(),
                    'papers': set(), 'full': set(), 'fractional': set(), 'fallback_papers': set()}
              for key in pool}
    for paper in papers:
        rows = by_doi.pop(paper['doi'], [])
        if paper['credit_status'] != 'ready':
            if rows:
                raise ValueError('Unresolved paper has credits')
            continue
        if not rows:
            raise ValueError('Ready paper lacks allocations')
        weight = Fraction(paper['journal_impact_factor'])
        if sum((Fraction(r['impact_factor_points_exact']) for r in rows), Fraction()) != weight:
            raise ValueError('JIF is not conserved over all institutions')
        if any(Fraction(r['fraction_exact']) != Fraction(1, len(rows)) or
               Fraction(r['impact_factor_points_exact']) != weight / len(rows) for r in rows):
            raise ValueError('Incorrect equal allocation')
        for row in rows:
            key = row['institution_id']
            if (row['eligible_arwu_top1000'] == 'true') != (key in pool):
                raise ValueError('Pool eligibility mismatch')
            if key not in pool:
                continue
            val = values[key]
            points = Fraction(row['impact_factor_points_exact'])
            provisional = row['correspondence_evidence_status'] == 'explicit_openalex_correspondence_PROVISIONAL'
            val['score'] += points
            val['fallback' if provisional else 'primary'] += points
            val['papers'].add(row['doi'])
            expected_type = 'full' if len(rows) == 1 else 'fractional'
            if row['credit_type'] != expected_type:
                raise ValueError('Credit type mismatch')
            val[expected_type].add(row['doi'])
            if provisional:
                val['fallback_papers'].add(row['doi'])
    if by_doi:
        raise ValueError('Credit references an unreviewed paper')
    result = []
    last_score = None
    rank = 0
    for position, key in enumerate(sorted(pool, key=lambda key: (-values[key]['score'], pool[key].casefold())), 1):
        val = values[key]
        if val['score'] != last_score:
            rank = position
        last_score = val['score']
        result.append({'rank': rank, 'institution_id': key, 'university': pool[key],
                       'total_impact_factor_score': format(float(val['score']), '.10f'),
                       'total_impact_factor_score_exact': str(val['score']),
                       'qualifying_papers': len(val['papers']),
                       'full_credit_papers': len(val['full']),
                       'fractional_credit_papers': len(val['fractional']),
                       'primary_correspondence_score_exact': str(val['primary']),
                       'openalex_fallback_score_exact': str(val['fallback']),
                       'openalex_fallback_papers': len(val['fallback_papers']),
                       'dataset_status': 'PROVISIONAL_INCOMPLETE_SCREENING_OBSERVED_CREDITS_ONLY'})
    return result


def main():
    def read(name):
        with (ROOT / 'data' / name).open() as stream:
            return list(csv.DictReader(stream))
    pool_rows = read('arwu_2026_top1000.csv')
    pool = {r['institution_id']: r['university'] for r in pool_rows}
    if len(pool) != 1000:
        raise ValueError('Expected exactly 1,000 eligible institutions')
    papers = read('papers_reviewed_PROVISIONAL.csv')
    credits = read('paper_credits_PROVISIONAL.csv')
    if len({p['doi'] for p in papers}) != len(papers):
        raise ValueError('Duplicate included DOI')
    for p in papers:
        if not START <= p['publication_date'] <= END:
            raise ValueError('Paper outside date window')
    ranking = aggregate(pool, papers, credits)
    save('university_scores_all1000_PROVISIONAL.csv', list(ranking[0]), ranking)
    # Include every exact-score tie at the cutoff; no secondary performance metric.
    top = [r for r in ranking if r['rank'] <= 100]
    save('top100_PROVISIONAL.csv', list(ranking[0]), top)
    top_ids = {r['institution_id'] for r in top}
    supplement = [r for r in credits if r['institution_id'] in top_ids]
    save('top100_paper_contributions_PROVISIONAL.csv', list(credits[0]), supplement)
    decisions = screening_decisions()
    summary = {'publication_start': START, 'publication_end': END,
               'eligible_institutions': 1000, 'included_papers': len(papers),
               'fully_allocated_papers': sum(p['credit_status'] == 'ready' for p in papers),
               'fallback_papers_included': sum(p['correspondence_evidence_status'] == 'explicit_openalex_correspondence_PROVISIONAL' for p in papers),
               'top100_rows_including_cutoff_ties': len(top),
               'unresolved_scientific_reviews': sum(d['decision'] in {'needs_abstract_review', 'needs_fuller_relevance_review'} for d in decisions.values()),
               'final_ranking_ready': False, 'arithmetic_checks_passed': True,
               'limitations': ['Scientific screening and primary access/eligibility review remain incomplete.',
                               'Missing institutions and papers are not zero research output; rankings can change substantially.',
                               'OpenAlex correspondence fallback is database-derived and not publisher-confirmed.',
                               'Papers with incomplete institutional denominators receive no scores until resolved.',
                               'Outside-pool institutions retain shares; those shares are not redistributed.',
                               'Some JIF values await primary-source confirmation; consult journal_impact_factors.csv.',
                               'Publication and indexing delays prevent a claim of exhaustive coverage.']}
    (ROOT / 'data/provisional_ranking_status.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
