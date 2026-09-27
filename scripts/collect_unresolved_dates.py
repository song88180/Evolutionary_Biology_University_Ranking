"""Fetch publisher Crossref deposits for unresolved primary publication dates."""
import concurrent.futures
import json
import time
from urllib.parse import quote

from collect_inventory import ROOT, fetch


def collect(doi):
    url = 'https://api.crossref.org/works/' + quote(doi, safe='/')
    try:
        record = json.loads(fetch(url))['message']
        if record['DOI'].lower() != doi:
            raise ValueError('DOI mismatch')
        record['source_url'] = url
        return {'doi': doi, 'record': record}
    except Exception as error:
        return {'doi': doi, 'error': str(error)}
    finally:
        time.sleep(0.6)


def main():
    rows = [json.loads(p.read_text()) for p in (ROOT / 'data/articles').glob('*.json')]
    dois = sorted({r['doi'] for r in rows if r.get('extraction_status') == 'repository_links_need_review' and not r.get('publisher_date')})
    path = ROOT / 'data/crossref_date_evidence.json'
    previous = {r['doi']: r for r in json.loads(path.read_text())} if path.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for result in executor.map(collect, dois):
            previous[result['doi']] = result
            print(result['doi'], 'record_received' if 'record' in result else 'failed', flush=True)
    path.write_text(json.dumps(list(previous.values()), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
