"""Prepare user-authorized provisional correspondence, never primary evidence.

Only manually screened evolutionary inclusions enter this queue. Eligibility
(date and original article type) and complete institutional normalization remain
separate gates. Existing publisher/repository records are never overwritten.
OpenAlex field semantics: https://help.openalex.org/data/authorships/
"""
from collections import Counter
import csv
import json

from collect_openalex_inventory import work_cache_path
from study_config import ROOT, screening_decisions

PRIMARY = {'explicit_publisher_links_parsed', 'explicit_repository_links_parsed'}


def provisional_correspondence(work, doi, primary=None):
    primary = primary or {}
    if primary.get('extraction_status') in PRIMARY:
        raise ValueError('Primary correspondence takes precedence')
    if primary.get('corresponding_authors'):
        raise ValueError('Accessible primary correspondence needs review, not replacement')
    returned = (work.get('doi') or '').lower().removeprefix('https://doi.org/')
    if returned != doi.lower():
        raise ValueError('DOI mismatch')
    authorships = work.get('authorships') or []
    if len(authorships) >= 100:
        raise ValueError('Possible 100-author truncation; complete denominator unverified')
    selected = [a for a in authorships if a.get('is_corresponding') is True]
    if not selected:
        raise ValueError('No explicitly marked OpenAlex corresponding authors')
    ids = {a.get('author', {}).get('id') for a in selected}
    # An author flagged is_corresponding but lacking a resolved OpenAlex author
    # id contributes None to ids; that is a linking gap, not a disagreement,
    # so it is excluded before comparing against the work-level declared set.
    resolved_ids = {i for i in ids if i}
    declared = set(work.get('corresponding_author_ids') or [])
    if declared and declared != resolved_ids:
        raise ValueError('Work-level and authorship correspondence identifiers disagree')
    authors = []
    for a in selected:
        name = a.get('raw_author_name') or a.get('author', {}).get('display_name')
        raw = a.get('raw_affiliation_strings') or []
        links = a.get('affiliations') or []
        # Preserve every raw string, including unresolved or joint institutions.
        # Do not silently substitute a smaller set of normalized institutions.
        for link in links:
            value = link.get('raw_affiliation_string')
            if value and value not in raw:
                raw = [*raw, value]
        if not name or not raw or any(not isinstance(s, str) or not s.strip() for s in raw):
            raise ValueError('Corresponding author lacks name or complete raw affiliations')
        authors.append({'name': name, 'author_id': a.get('author', {}).get('id'),
                        'affiliations': [{'affiliation_id': f'openalex-{n}', 'address': s}
                                         for n, s in enumerate(dict.fromkeys(raw), 1)],
                        'openalex_institution_records': a.get('institutions') or [],
                        'raw_affiliation_to_institution_links': links})
    return {'doi': doi, 'corresponding_authors': authors,
            'extraction_status': 'explicit_openalex_correspondence_PROVISIONAL',
            'source_url': 'https://api.openalex.org/works/' + work['id'].split('/')[-1],
            'openalex_id': work['id'],
            'correspondence_limitation': 'Database correspondence and affiliations; not publisher-confirmed. Missing source annotations may omit corresponding authors.'}


def main():
    decisions = screening_decisions()
    audit = {r['doi']: r for r in csv.DictReader((ROOT / 'data/screening_audit_INCOMPLETE.csv').open()) if r['doi']}
    failures = {}
    for filename in ('pmc_collection_status.json', 'pmc_html_collection_status.json', 'nature_priority_collection_status.json'):
        path = ROOT / 'data' / filename
        if path.exists():
            payload = json.loads(path.read_text())
            if isinstance(payload, list):
                for item in payload:
                    failures.setdefault(item.get('doi'), []).append(item)
    restricted = {'Science', 'Science Advances', 'Cell', 'Current Biology',
                  'Proceedings of the National Academy of Sciences'}
    evidence, queue = {}, []
    for doi, decision in sorted(decisions.items()):
        if decision['decision'] not in {'include', 'include_pending_primary_evidence'} or doi not in audit:
            continue
        row = audit[doi]
        path = ROOT / 'data/articles' / (doi.split('/')[-1] + '.json')
        primary = json.loads(path.read_text()) if path.exists() else {}
        if primary.get('extraction_status') in PRIMARY:
            continue
        attempted = failures.get(doi, [])
        repository_failed = any('fail' in a.get('status', '') for a in attempted)
        access_basis = ''
        if row['journal'] in restricted and (not row['pmcid'] or repository_failed):
            access_basis = 'Publisher access restrictions documented in data/access_issues.csv; ' + ('repository extraction failed' if row['pmcid'] else 'no PMC record in reconciled inventory')
        elif repository_failed or primary.get('extraction_status') == 'failed':
            access_basis = 'Article-specific primary collection failure documented in collection status'
        result = {'doi': doi, 'journal': row['journal'], 'title': row['title']}
        try:
            if not access_basis:
                raise ValueError('Primary access/evidence review remains necessary')
            cached = work_cache_path(doi)
            if not cached.exists():
                raise ValueError('OpenAlex work absent from local cache')
            payload = json.loads(cached.read_text())
            record = provisional_correspondence(payload['work'], doi, primary)
            record.update({'primary_access_limitation': access_basis,
                           'primary_collection_attempts': attempted,
                           'openalex_retrieval_url': payload['source_url']})
            evidence[doi] = record
            result['status'] = 'correspondence_ready_other_eligibility_gates_pending'
        except ValueError as error:
            result.update(status='held', reason=str(error))
        queue.append(result)
    (ROOT / 'data/openalex_fallback_correspondence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    report = {'statuses': dict(Counter(r['status'] for r in queue)),
              'held_reasons': dict(Counter(r.get('reason') for r in queue if r['status'] == 'held')),
              'records': queue, 'scored': False}
    (ROOT / 'data/openalex_fallback_status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__':
    main()
