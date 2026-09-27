"""Display bounded evidence batches for individual scientific review.

This read-only helper makes no screening decisions. OpenAlex topics are never
used as automatic inclusion or exclusion rules.
"""
import argparse
import csv
import json
import hashlib
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from pathlib import Path
from study_config import ROOT, INVENTORY, screening_decisions
from reconcile_inventory import abstract_text

PREFIX_SLUGS = {'10.1126/sciadv.': 'sciadv', '10.1126/science.': 'science',
               '10.1016/j.cell.': 'cell', '10.1016/j.cub.': 'cub',
               '10.1073/pnas.': 'pnas', '10.1093/molbev/': 'mbe',
               '10.1038/s41467-': 'ncomms', '10.1038/s41559-': 'natecolevol',
               '10.1038/s41588-': 'ng', '10.1038/s41562-': 'nathumbehav',
               '10.1038/s41586-': 'nature'}


def inventories(dois, suffix):
    slugs = {slug for doi in dois for prefix, slug in PREFIX_SLUGS.items() if doi.startswith(prefix)}
    recognized = all(any(doi.startswith(prefix) for prefix in PREFIX_SLUGS) for doi in dois)
    return sorted(INVENTORY.glob('*_' + suffix + '.json')) if not recognized else [INVENTORY / (slug + '_' + suffix + '.json') for slug in sorted(slugs)]


def rows(journal):
    decisions = screening_decisions()
    return [r for r in csv.DictReader((ROOT / 'data/screening_audit_INCOMPLETE.csv').open())
            if r['journal'] == journal and r['record_id'] not in decisions
            and r['review_status'] == 'unreviewed']


def abstracts(dois):
    result = {}
    for doi in dois:
        path = ROOT / 'data/articles' / (doi.split('/')[-1] + '.json')
        if path.exists():
            a = json.loads(path.read_text())
            # Older parsed PMC records may contain only PNAS Significance.
            # Read every cached primary abstract section before scientific review.
            url = a.get('source_url') or a.get('article_url', '')
            cached = ROOT / 'data/sources' / (hashlib.sha256(url.encode()).hexdigest() + '.body')
            if 'pmc.ncbi.nlm.nih.gov/articles/' in url and cached.exists():
                soup = BeautifulSoup(cached.read_text(), 'html.parser')
                nodes = soup.select('.abstract')
                nodes = [n for n in nodes if not any(p in nodes for p in n.parents)]
                if nodes:
                    a['abstract'] = '\n'.join(n.get_text(' ', strip=True) for n in nodes)
            if a.get('abstract'):
                result[doi] = {'doi': doi, 'title': a.get('title'), 'abstract': a['abstract'],
                               'source': a.get('source_url', a.get('article_url')), 'evidence': 'primary article abstract'}
    refreshed_path = ROOT / 'data/review_metadata_refresh.json'
    refreshed = json.loads(refreshed_path.read_text()) if refreshed_path.exists() else {}
    for doi in dois:
        if doi in result:
            continue
        for a in refreshed.get(doi, {}).get('records', []):
            if a.get('doi', '').lower() == doi.lower() and a.get('abstractText'):
                result[doi] = {'doi': doi, 'title': a.get('title'), 'abstract': a['abstractText'],
                               'source': refreshed[doi]['source_url'], 'evidence': 'refreshed Europe PMC abstract'}
                break
    for p in inventories(dois, 'epmc'):
        if len(result) == len(dois):
            break
        for a in json.loads(p.read_text())['records']:
            doi = a.get('doi', '').lower()
            if doi in dois and doi not in result and a.get('abstractText'):
                result[doi] = {'doi': doi, 'title': a.get('title'), 'abstract': a['abstractText'],
                               'source': 'Europe PMC record ' + a['id'], 'evidence': 'Europe PMC abstract'}
    for p in inventories(dois, 'openalex'):
        if len(result) == len(dois):
            break
        for a in json.loads(p.read_text())['records']:
            doi = (a.get('doi') or '').removeprefix('https://doi.org/').lower()
            if doi in dois and doi not in result and a.get('abstract_inverted_index'):
                result[doi] = {'doi': doi, 'title': a.get('title'), 'abstract': abstract_text(a['abstract_inverted_index']),
                               'source': a['id'], 'evidence': 'OpenAlex abstract'}
    return [result.get(doi, {'doi': doi, 'abstract': '', 'evidence': 'abstract unavailable in current cache'}) for doi in dois]


def article_evidence(doi, pattern, limit, last=False, section=None):
    """Return contextual primary excerpts, not a claim of full-text review."""
    path = ROOT / 'data/articles' / (doi.split('/')[-1] + '.json')
    if not path.exists():
        # Correspondence extraction can fail even when primary text is usable.
        # Scientific review must not treat a byline-parser failure as missing text.
        audit = ROOT / 'data/screening_audit_INCOMPLETE.csv'
        with audit.open() as stream:
            row = next((r for r in csv.DictReader(stream) if r['doi'] == doi and r.get('pmcid')), None)
        if row is None:
            refreshed_path = ROOT / 'data/review_metadata_refresh.json'
            refreshed = json.loads(refreshed_path.read_text()) if refreshed_path.exists() else {}
            row = next((r for r in refreshed.get(doi, {}).get('records', [])
                        if r.get('doi', '').lower() == doi.lower() and r.get('pmcid')), None)
        if row is None:
            return {'doi': doi, 'error': 'No cached primary article record'}
        urls = ['https://www.ebi.ac.uk/europepmc/webservices/rest/' + row['pmcid'] + '/fullTextXML',
                'https://pmc.ncbi.nlm.nih.gov/articles/' + row['pmcid'] + '/']
        article = None
        for url in urls:
            cached = ROOT / 'data/sources' / (hashlib.sha256(url.encode()).hexdigest() + '.body')
            if not cached.exists():
                continue
            if 'fullTextXML' in url:
                try:
                    tree = ET.fromstring(cached.read_text())
                    valid = any((e.text or '').lower() == doi.lower() for e in
                                tree.findall("front/article-meta/article-id[@pub-id-type='doi']"))
                except ET.ParseError:
                    valid = False
            else:
                soup = BeautifulSoup(cached.read_text(), 'html.parser')
                meta = soup.find('meta', attrs={'name': 'citation_doi'})
                valid = bool(meta and meta.get('content', '').lower() == doi.lower())
            if valid:
                article = {'source_url': url}
                break
        if article is None:
            return {'doi': doi, 'error': 'Cached repository text does not verify requested DOI'}
    else:
        article = json.loads(path.read_text())
    url = article.get('source_url') or article.get('article_url', '')
    cached = ROOT / 'data/sources' / (hashlib.sha256(url.encode()).hexdigest() + '.body')
    if cached.exists() and ('pmc.ncbi.nlm.nih.gov/articles/' in url or 'nature.com/articles/' in url):
        soup = BeautifulSoup(cached.read_text(), 'html.parser')
        body = soup.select_one('.main-article-body, .c-article-body')
        if body is None:
            return {'doi': doi, 'error': 'No primary HTML article body', 'source': url}
        paras = []
        for p in body.find_all('p'):
            names = []
            for parent in p.parents:
                if parent is body:
                    break
                if parent.name == 'section':
                    heading = parent.find(['h2', 'h3', 'h4', 'h5'], recursive=False)
                    title = parent.get('data-title') or (heading.get_text(' ', strip=True) if heading else '')
                    if title:
                        names.append(title)
            path = ' / '.join(reversed(names))
            value = p.get_text(' ', strip=True)
            if re.search(pattern, value, re.I) and (not section or re.search(section, path, re.I)):
                paras.append({'section': path, 'text': value})
        return {'doi': doi, 'source': url,
                'section_titles': [h.get_text(' ', strip=True) for h in body.find_all(['h2', 'h3', 'h4'])],
                'matching_paragraph_count': len(paras), 'selected_paragraphs': paras[-limit:] if last else paras[:limit]}
    if 'fullTextXML' not in url or not cached.exists():
        return {'doi': doi, 'error': 'No cached primary JATS body', 'source': url}
    tree = ET.fromstring(cached.read_text())
    body = tree.find('body')
    if body is None:
        return {'doi': doi, 'error': 'No article body', 'source': url}
    parents = {c: p for p in tree.iter() for c in p}
    def section_path(node):
        names = []
        while node in parents:
            node = parents[node]
            if node.tag == 'sec':
                title = node.find('title')
                if title is not None:
                    names.append(' '.join(''.join(title.itertext()).split()))
        return ' / '.join(reversed(names))
    paras = []
    for p in body.iter('p'):
        value = ' '.join(''.join(p.itertext()).split())
        path = section_path(p)
        if re.search(pattern, value, re.I) and (not section or re.search(section, path, re.I)):
            paras.append({'section': path, 'text': value})
    return {'doi': doi, 'source': url,
            'section_titles': [' '.join(''.join(t.itertext()).split()) for t in body.iter('title')],
            'matching_paragraph_count': len(paras), 'selected_paragraphs': paras[-limit:] if last else paras[:limit]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--abstract', nargs='+')
    parser.add_argument('--article-evidence', nargs='+')
    parser.add_argument('--pattern', default=r'evolut|ancestr|phylogen|selection|domest|fitness|horizontal|gene loss')
    parser.add_argument('--paragraph-limit', type=int, default=8)
    parser.add_argument('--last-paragraphs', action='store_true', help='Show the last matching contextual paragraphs instead of the first')
    parser.add_argument('--section', help='Restrict contextual evidence to matching section paths')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.article_evidence:
        for doi in args.article_evidence:
            print(json.dumps(article_evidence(doi, args.pattern, args.paragraph_limit, args.last_paragraphs, args.section), ensure_ascii=False))
    elif args.abstract:
        for a in abstracts(args.abstract):
            print(json.dumps(a, ensure_ascii=False))
    else:
        selected = rows(args.journal)[args.start:args.start + args.limit]
        if args.json:
            print(json.dumps([{'doi': r['doi'], 'title': r['title'], 'journal': r['journal'], 'record_id': r['record_id']}
                              for r in selected], ensure_ascii=False))
        else:
            for n, r in enumerate(selected, args.start):
                print(f"{n} {r['doi']} {r['title']}")
