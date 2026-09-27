"""Read-only audit of cached author-linked OpenAlex evidence for held addresses."""
import collections
import csv
import json
from pathlib import Path

from collect_openalex_inventory import work_cache_path
from export_reviewed import normalized

ROOT = Path(__file__).resolve().parents[1]


def main():
    queue = list(csv.DictReader((ROOT / 'data/unresolved_affiliations_PROVISIONAL.csv').open()))
    counts = collections.Counter()
    examples = collections.defaultdict(list)
    contained_names = collections.Counter()
    contained_rows = []
    for row in queue:
        path = work_cache_path(row['doi'])
        if not path.exists():
            status = 'no_work_cache'
        else:
            work = json.loads(path.read_text())['work']
            authors = [a for a in work.get('authorships', [])
                       if normalized(a.get('author', {}).get('display_name', ''))
                       == normalized(row['corresponding_author'])]
            if len(authors) != 1:
                status = 'author_mismatch'
            else:
                author = authors[0]
                links = [a for a in author.get('affiliations', [])
                         if normalized(a.get('raw_affiliation_string', '')) == normalized(row['affiliation'])]
                if len(links) != 1:
                    status = 'address_mismatch'
                else:
                    ids = links[0].get('institution_ids', [])
                    if not ids:
                        status = 'no_institution_link'
                    elif len(ids) != 1:
                        status = 'multiple_institution_links'
                    else:
                        inst = [i for i in author.get('institutions', []) if i.get('id') == ids[0]]
                        if len(inst) != 1:
                            status = 'missing_institution_record'
                        else:
                            name = inst[0].get('display_name', '')
                            status = 'single_name_contained' if normalized(name) in normalized(row['affiliation']) else 'single_name_not_contained'
                            row = {**row, 'openalex_institution': name, 'ror': inst[0].get('ror')}
                            if row['ror']:
                                cached_ror = ROOT / 'data/ror_records' / (row['ror'].split('/')[-1] + '.json')
                                if cached_ror.exists():
                                    record = json.loads(cached_ror.read_text())['record']
                                    row['ror_types'] = record.get('types', [])
                                    row['ror_parents'] = [r['label'] for r in record.get('relationships', []) if r['type'] == 'parent']
                            if status == 'single_name_contained':
                                contained_names[name] += 1
                                contained_rows.append(row)
        counts[status] += 1
        if len(examples[status]) < 5:
            examples[status].append(row)
    print(json.dumps({'counts': counts, 'contained_names': contained_names,
                      'contained_rows': contained_rows, 'examples': examples}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
