"""Resolve missing online dates from explicit electronic ArticleDate metadata."""
import argparse
import csv
import json
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from collect_inventory import ROOT, fetch
from study_config import screening_decisions


def electronic_dates(xml):
    records = {}
    root = ET.fromstring(xml)
    for pub in root.findall('PubmedArticle'):
        article = pub.find('MedlineCitation/Article')
        pmid = pub.findtext('MedlineCitation/PMID')
        dois = {e.text.lower() for e in pub.findall('PubmedData/ArticleIdList/ArticleId')
                if e.get('IdType') == 'doi' and e.text}
        if len(dois) != 1 or article is None:
            continue
        dates = []
        for date in article.findall('ArticleDate'):
            if date.get('DateType') != 'Electronic':
                continue
            try:
                dates.append(f"{int(date.findtext('Year')):04d}-{int(date.findtext('Month')):02d}-{int(date.findtext('Day')):02d}")
            except (ValueError, TypeError):
                continue
        if dates:
            records[next(iter(dois))] = {'pmid': pmid, 'online_date': min(dates),
                                        'evidence': 'PubMed ArticleDate DateType=Electronic'}
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-candidates', action='store_true',
                        help='Also collect electronic dates for screened inclusions lacking primary correspondence')
    args = parser.parse_args()
    pending = []
    for path in (ROOT / 'data/articles').glob('*.json'):
        article = json.loads(path.read_text())
        if article.get('extraction_status') == 'repository_links_need_review' and not article.get('publisher_date') and article.get('pmid'):
            pending.append((path, article))
    evidence_path = ROOT / 'data/pubmed_date_evidence.json'
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    candidates = [a for _, a in pending]
    if args.review_candidates:
        decisions = screening_decisions()
        with (ROOT / 'data/screening_audit_INCOMPLETE.csv').open() as stream:
            candidates.extend(r for r in csv.DictReader(stream)
                              if r['pmid'] and decisions.get(r['doi'], {}).get('decision')
                              in {'include', 'include_pending_primary_evidence'})
    ids = sorted({a['pmid'] for a in candidates if a['doi'] not in evidence})
    for start in range(0, len(ids), 100):
        url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urlencode({'db': 'pubmed', 'id': ','.join(ids[start:start+100]), 'retmode': 'xml'})
        found = electronic_dates(fetch(url))
        for doi, record in found.items():
            evidence[doi] = {**record, 'source_url': url}
        evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps({'requested_pmids': min(start + 100, len(ids)),
                          'total_pmids': len(ids), 'dates_in_batch': len(found)}), flush=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    resolved = 0
    for path, article in pending:
        result = evidence.get(article['doi'])
        if not result:
            continue
        article['publisher_date'] = result['online_date']
        article['date_evidence'] = 'publisher_electronic_article_date_in_pubmed'
        article['publication_date_source_url'] = result['source_url']
        if not article.get('unlinked_correspondence_notes'):
            article['extraction_status'] = 'explicit_repository_links_parsed'
        path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + '\n')
        resolved += 1
    print(json.dumps({'pending': len(pending), 'electronic_dates_resolved': resolved}))


if __name__ == '__main__':
    main()
