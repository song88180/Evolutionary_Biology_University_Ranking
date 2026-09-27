"""Cache public ROR records linked to held corresponding-author affiliations.

ROR identities are review aids, not automatic eligibility or credit decisions.
"""
import concurrent.futures
import csv
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

from collect_openalex_inventory import work_cache_path
from export_reviewed import normalized

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/ror_records'


def ror_ids():
    ids = set()
    queue = csv.DictReader((ROOT / 'data/unresolved_affiliations_PROVISIONAL.csv').open())
    for row in queue:
        path = work_cache_path(row['doi'])
        if not path.exists():
            continue
        work = json.loads(path.read_text())['work']
        for author in work.get('authorships', []):
            if normalized(author.get('author', {}).get('display_name', '')) != normalized(row['corresponding_author']):
                continue
            for aff in author.get('affiliations', []):
                if normalized(aff.get('raw_affiliation_string', '')) != normalized(row['affiliation']):
                    continue
                linked = set(aff.get('institution_ids', []))
                for inst in author.get('institutions', []):
                    if inst.get('id') in linked and inst.get('ror', '').startswith('https://ror.org/'):
                        ids.add(inst['ror'].split('/')[-1])
    return sorted(ids)


def collect(identifier):
    target = CACHE / f'{identifier}.json'
    if target.exists():
        return identifier, 'cached'
    url = f'https://api.ror.org/v2/organizations/{identifier}'
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'EvoRankingResearch/1.0 (public organizational identity verification)'})
            with urlopen(request, timeout=20) as response:
                record = json.load(response)
            if record.get('id') != f'https://ror.org/{identifier}':
                raise ValueError(f'ROR identifier mismatch: {identifier}')
            target.write_text(json.dumps({'record': record, 'source_url': url}, ensure_ascii=False) + '\n')
            return identifier, 'collected'
        except Exception as error:
            if attempt == 2:
                return identifier, f'error: {error}'
            time.sleep(attempt + 1)


def main():
    CACHE.mkdir(exist_ok=True)
    identifiers = ror_ids()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(collect, identifiers))
    counts = {}
    for _, status in results:
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({'ror_ids': len(identifiers), 'statuses': counts}))


if __name__ == '__main__':
    main()
