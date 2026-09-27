"""Apply reviewed resolutions for the 2026-09-27 held-affiliation queue.

The integer keys refer to the numbered, DOI-checked snapshot of
unresolved_affiliations_PROVISIONAL.csv. Run only while that snapshot matches.
OpenAlex author-linked institutions were accepted as authoritative where
available; publisher-listed affiliations fill explicit OpenAlex omissions.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

# Empty tuples are administrative projects/laboratories already represented
# by a separately listed employer affiliation for the same author.
RESOLUTIONS = {
 1: ('outside:howard-hughes-medical-institute', 'stanford-university'),
 2: ('lund-university',),
 3: ('northwestern-university',),
 4: ('university-of-padua',),
 5: ('outside:national-biodiversity-future-center',),
 6: ('outside:csic', 'outside:university-of-cantabria'),
 7: ('outside:covid-19-international-research-team',),
 8: ('outside:poblar-argentina',),
 9: (),
 10: ('outside:china-pakistan-joint-research-center-earth-sciences',),
 11: (),
 12: ('outside:chinese-medicine-guangdong-laboratory',),
 13: ('east-china-normal-university',),
 14: ('east-china-normal-university',),
 15: (),
 16: (),
 17: (),
 18: (),
 19: (),
 20: (),
 21: (),
 22: ('outside:bama-rural-revitalization-research-institute',),
 23: (),
 24: ('dartmouth-college',),
 25: ('outside:university-of-burgos',),
 26: ('outside:university-of-cantabria',),
 27: ('outside:university-of-the-ryukyus',),
 28: ('outside:united-states-geological-survey',),
 29: ('outside:guangzhou-laboratory',),
 30: ('outside:georgian-national-museum',),
 31: ('outside:tbilisi-state-university',),
 32: ('outside:konan-university',),
 33: ('outside:konan-university',),
 34: ('outside:konan-university',),
 35: ('outside:konan-university',),
 36: ('outside:konan-university',),
 37: ('outside:konan-university',),
 38: ('outside:institute-of-automation-cas',),
 39: ('outside:institute-of-automation-cas',),
 40: ('outside:university-of-health-and-rehabilitation-sciences',),
 41: ('outside:shandong-medical-and-pharmaceutical-university',),
 42: ('outside:guangzhou-laboratory',),
 43: ('outside:cnrs', 'psl-university'),
 44: ('outside:cnrs',),
 45: ('outside:cnrs',),
 46: ('outside:cnrs', 'sorbonne-university'),
 47: ('outside:cnrs', 'psl-university', 'outside:ird', 'university-of-montpellier'),
 48: ('outside:cnrs', 'paris-saclay-university', 'outside:agroparistech'),
 49: ('outside:cnrs', 'psl-university', 'outside:ird', 'university-of-montpellier'),
 50: ('outside:geological-survey-of-india',),
 51: ('outside:parmenides-foundation',),
 52: ('outside:hun-ren-centre-for-ecological-research',),
 53: ('outside:tanzania-national-parks',),
 54: ('outside:bavarian-natural-history-collections',),
 55: ('outside:swiss-institute-of-bioinformatics',),
 56: ('outside:institut-pasteur', 'university-of-paris', 'outside:cnrs'),
 57: ('outside:cnrs', 'outside:inserm', 'outside:university-of-saint-etienne'),
 58: ('university-of-montpellier', 'outside:cnrs', 'psl-university', 'outside:ird'),
 59: ('outside:howard-hughes-medical-institute', 'university-of-california-berkeley'),
 60: ('outside:gladstone-institutes', 'university-of-california-san-francisco'),
}

NEW_OUTSIDE = {
 'outside:csic': 'Consejo Superior de Investigaciones Científicas (CSIC)',
 'outside:covid-19-international-research-team': 'COVID-19 International Research Team',
 'outside:poblar-argentina': 'PoblAr Argentina genomic biobank programme',
 'outside:china-pakistan-joint-research-center-earth-sciences': 'China-Pakistan Joint Research Center on Earth Sciences',
 'outside:chinese-medicine-guangdong-laboratory': 'Chinese Medicine Guangdong Laboratory',
 'outside:bama-rural-revitalization-research-institute': 'Bama Yao Autonomous County Rural Revitalization Research Institute',
 'outside:university-of-burgos': 'University of Burgos',
 'outside:university-of-the-ryukyus': 'University of the Ryukyus',
 'outside:united-states-geological-survey': 'United States Geological Survey',
 'outside:georgian-national-museum': 'Georgian National Museum',
 'outside:tbilisi-state-university': 'Tbilisi State University',
 'outside:konan-university': 'Konan University',
 'outside:institute-of-automation-cas': 'Institute of Automation, Chinese Academy of Sciences',
 'outside:university-of-health-and-rehabilitation-sciences': 'University of Health and Rehabilitation Sciences',
 'outside:shandong-medical-and-pharmaceutical-university': 'Shandong Medical and Pharmaceutical University',
 'outside:agroparistech': 'AgroParisTech',
 'outside:geological-survey-of-india': 'Geological Survey of India',
 'outside:parmenides-foundation': 'Parmenides Foundation',
 'outside:tanzania-national-parks': 'Tanzania National Parks',
 'outside:bavarian-natural-history-collections': 'Bavarian Natural History Collections',
 'outside:university-of-saint-etienne': 'Jean Monnet University Saint-Étienne',
}

def main():
    rows = list(csv.DictReader((DATA / 'unresolved_affiliations_PROVISIONAL.csv').open()))
    assert len(rows) == 60 and set(RESOLUTIONS) == set(range(1, 61)), 'Queue changed; re-review before applying'
    assert rows[0]['doi'] == '10.1016/j.cub.2026.02.052'
    assert rows[-1]['doi'] == '10.1126/science.aei0498'
    outside_path = DATA / 'institutions_outside_pool.json'
    outside = json.loads(outside_path.read_text())
    for key, name in NEW_OUTSIDE.items():
        if key in outside and outside[key] != name:
            raise ValueError('Registry conflict: ' + key)
        outside[key] = name
    universe = {r['institution_id'] for r in csv.DictReader((DATA / 'arwu_2026_top1000.csv').open())} | set(outside)
    overrides_path = DATA / 'affiliation_overrides.json'
    overrides = json.loads(overrides_path.read_text())
    for index, row in enumerate(rows, 1):
        ids = list(RESOLUTIONS[index])
        if set(ids) - universe:
            raise ValueError(f'Unknown institution ID at row {index}: {set(ids)-universe}')
        address = row['affiliation']
        if address in overrides:
            existing = overrides[address]
            if existing['institution_ids'] != ids:
                raise ValueError(f'Conflicting resolution for shared address at row {index}')
            if row['doi'] not in existing['only_for_dois']:
                existing['only_for_dois'].append(row['doi'])
            continue
        reason = ('OpenAlex author-linked institution identity, with separately named home institutions retained.'
                  if ids else 'Research programme, shared laboratory, or administrative unit; author has a separately listed home institution.')
        overrides[address] = {'institution_ids': ids, 'reason': reason,
                              'source_url': 'https://doi.org/' + row['doi'],
                              'only_for_dois': [row['doi']]}
        if not ids:
            overrides[address]['administrative_zero_credit'] = True
    outside_path.write_text(json.dumps(dict(sorted(outside.items())), ensure_ascii=False, indent=2) + '\n')
    overrides_path.write_text(json.dumps(dict(sorted(overrides.items())), ensure_ascii=False, indent=2) + '\n')
    print(f'Resolved {len(rows)} queued affiliations across {len({r["doi"] for r in rows})} papers')

if __name__ == '__main__':
    main()
