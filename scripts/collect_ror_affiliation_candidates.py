"""Cache ROR suggestions for held addresses; never assign credit automatically."""
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/ror_affiliation_search'


def cache_path(address):
    return CACHE / (hashlib.sha256(address.encode()).hexdigest() + '.json')


def collect(address):
    target = cache_path(address)
    if target.exists():
        return 'cached'
    url = 'https://api.ror.org/v2/organizations?' + urlencode({'affiliation': address})
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'EvoRankingResearch/1.0 (public affiliation candidate audit)'})
            with urlopen(request, timeout=25) as response:
                payload = json.load(response)
            candidates = []
            for item in payload.get('items', [])[:5]:
                record = item['organization']
                name = next(n['value'] for n in record['names'] if 'ror_display' in n['types'])
                candidates.append({'ror': record['id'], 'name': name,
                                   'chosen': item.get('chosen', False),
                                   'matching_type': item.get('matching_type', ''),
                                   'types': record.get('types', []),
                                   'parents': [r['label'] for r in record.get('relationships', []) if r['type'] == 'parent']})
            target.write_text(json.dumps({'address': address, 'source_url': url,
                                          'candidates': candidates}, ensure_ascii=False) + '\n')
            return 'collected'
        except Exception as error:
            if attempt == 2:
                return f'error: {error}'
            time.sleep(attempt + 1)


def main():
    CACHE.mkdir(exist_ok=True)
    rows = list(csv.DictReader((ROOT / 'data/unresolved_affiliations_PROVISIONAL.csv').open()))
    addresses = list(dict.fromkeys(row['affiliation'] for row in rows))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(collect, addresses))
    counts = {}
    for status in statuses:
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({'unique_addresses': len(addresses), 'statuses': counts}))


if __name__ == '__main__':
    main()
