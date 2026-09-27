"""Refresh metadata for unresolved reviews without changing discovery or eligibility.

Snapshots are separate from the frozen discovery inventories. Neither article
type nor an abstract automatically authorizes inclusion or correspondence credit.
"""
import argparse
from collections import Counter
import concurrent.futures
from datetime import datetime, timezone
import json
from urllib.parse import urlencode

from collect_inventory import fetch
from study_config import ROOT, screening_decisions


def collect(doi):
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode({
        'query': 'DOI:"' + doi + '"', 'format': 'json', 'resultType': 'core', 'pageSize': 10})
    try:
        result = json.loads(fetch(url))
        matches = [r for r in result.get('resultList', {}).get('result', [])
                   if r.get('doi', '').lower() == doi.lower()]
        records = sorted(matches, key=lambda r: (r.get('source') != 'MED', not bool(r.get('abstractText'))))
        return doi, {'status': 'found' if records else 'not_found', 'source_url': url,
                     'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'records': records}
    except Exception as error:
        return doi, {'status': 'failed', 'error': str(error), 'source_url': url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--doi', action='append')
    args = parser.parse_args()
    dois = args.doi or [d for d, v in screening_decisions().items()
                       if d.startswith('10.') and v['decision'] in
                       {'needs_abstract_review', 'needs_fuller_relevance_review'}]
    path = ROOT / 'data/review_metadata_refresh.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    counts = Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for doi, result in pool.map(collect, dois):
            previous[doi] = result
            counts[result['status']] += 1
            path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'doi': doi, 'status': result['status']}), flush=True)
    print(json.dumps(dict(counts)))


if __name__ == '__main__':
    main()
