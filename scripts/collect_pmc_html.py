"""Read explicit author-note links from public PMC HTML, without email inference."""
import argparse
from collections import Counter
import concurrent.futures
import csv
import json
import re
from bs4 import BeautifulSoup
from collect_inventory import ROOT, fetch
from collect_pmc_articles import is_contribution_note
from study_config import screening_decisions


def labels(value):
    return set(filter(None, re.split(r'[\s,;]+', value.strip())))


def parse(html, row):
    soup = BeautifulSoup(html, 'html.parser')
    meta = soup.find('meta', attrs={'name': 'citation_doi'})
    if not meta or meta.get('content', '').lower() != row['doi'].lower():
        raise ValueError('PMC HTML DOI mismatch')
    front = soup.select_one('.front-matter')
    if front is None:
        raise ValueError('PMC front matter missing')
    notes = {}
    for note in front.select('.author-notes .fn, .author-notes .corresp'):
        value = note.get_text(' ', strip=True)
        if not re.search(r'\bcorresponding authors?\b|\bcorrespondence\b', value, re.I):
            continue
        sup = note.find('sup', recursive=False)
        if sup is None:
            raise ValueError('Correspondence note has no explicit byline label')
        keys = labels(sup.get_text(' ', strip=True))
        if not keys:
            raise ValueError('Empty correspondence label')
        notes[note.get('id', value)] = (keys, value)
    if not notes:
        raise ValueError('No labeled correspondence notes')
    authors, represented = [], set()
    for link in front.select('.cg > a[aria-describedby]'):
        author_labels = set()
        for sib in link.next_siblings:
            if getattr(sib, 'name', None) == 'a' and sib.has_attr('aria-describedby'):
                break
            if getattr(sib, 'name', None) == 'sup':
                author_labels.update(labels(sib.get_text(' ', strip=True)))
        matched = {key for key, (keys, _) in notes.items() if keys & author_labels}
        if not matched:
            continue
        represented.update(matched)
        card = soup.find(id=link['aria-describedby'])
        affiliations = []
        if card:
            for block in card.find_all('div', recursive=False):
                sup = block.find('sup', recursive=False)
                if sup is None or block.find('a') is not None:
                    continue
                label = sup.get_text(' ', strip=True)
                copy = BeautifulSoup(str(block), 'html.parser')
                copy.sup.decompose()
                address = copy.get_text(' ', strip=True)
                if address and not is_contribution_note(address):
                    affiliations.append({'affiliation_id': label, 'address': address})
        if not affiliations:
            raise ValueError('Corresponding author lacks explicit affiliation card')
        authors.append({'name': link.get_text(' ', strip=True), 'affiliations': affiliations})
    if set(notes) != represented or not authors:
        raise ValueError('Not all correspondence notes are linked to parsed authors')
    abstracts = soup.select('.abstract')
    if not abstracts:
        abstracts = soup.select('#abstract1, #abstract')
    # PNAS exposes Significance and the scientific Abstract separately.
    # Keep both, without duplicating nested abstract containers.
    abstracts = [node for node in abstracts if not any(parent in abstracts for parent in node.parents)]
    title = front.find('h1')
    return {**row, 'title': title.get_text(' ', strip=True) if title else row['title'],
            'article_url': 'https://doi.org/' + row['doi'],
            'source_url': 'https://pmc.ncbi.nlm.nih.gov/articles/' + row['pmcid'] + '/',
            'publisher_date': '', 'date_evidence': 'online_date_unresolved',
            'article_type': row.get('publisher_article_type') or 'repository_article_type_unstated',
            'article_type_review_required': not bool(row.get('publisher_article_type')),
            'corresponding_authors': authors,
            'correspondence_statement': ' | '.join(value for _, value in notes.values()),
            'unlinked_correspondence_notes': [],
            'abstract': '\n'.join(node.get_text(' ', strip=True) for node in abstracts),
            'extraction_status': 'repository_links_need_review',
            'extraction_method': 'PMC HTML explicit correspondence footnote labels and author affiliation cards'}


def collect(row):
    path = ROOT / 'data/articles' / (row['doi'].split('/')[-1] + '.json')
    if path.exists():
        existing = json.loads(path.read_text())
        if existing.get('extraction_status') in {'explicit_publisher_links_parsed', 'explicit_repository_links_parsed', 'repository_links_need_review'}:
            return {'doi': row['doi'], 'status': 'existing_evidence'}
    try:
        result = parse(fetch('https://pmc.ncbi.nlm.nih.gov/articles/' + row['pmcid'] + '/'), row)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return {'doi': row['doi'], 'status': result['extraction_status']}
    except Exception as error:
        return {'doi': row['doi'], 'status': 'failed', 'error': str(error)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', action='append')
    args = parser.parse_args()
    decisions = screening_decisions()
    rows = [r for r in csv.DictReader((ROOT / 'data/screening_audit_INCOMPLETE.csv').open())
            if r['pmcid'] and (not args.journal or r['journal'] in args.journal)
            and decisions.get(r['doi'], {}).get('decision') in {'include_pending_primary_evidence', 'needs_abstract_review', 'needs_fuller_relevance_review'}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(collect, rows))
    path = ROOT / 'data/pmc_html_collection_status.json'
    previous = {r['doi']: r for r in json.loads(path.read_text())} if path.exists() else {}
    previous.update({r['doi']: r for r in results})
    path.write_text(json.dumps(list(previous.values()), indent=2) + '\n')
    print(json.dumps(dict(Counter(r['status'] for r in results))), flush=True)
