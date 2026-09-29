"""Explainable French FAQ retrieval using only Python's standard library."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

STOPWORDS = set('a au aux avec ce ces cette dans de des du en et est il je la le les ma mes mon ne nos notre on ou par pas pour que quel quelle quels quelles qui sa se ses son sur ta tes ton tu un une vos votre vous comment puis peux peut faire'.split())
METHODS = ('overlap', 'tfidf')


def tokens(text):
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return [word for word in re.findall(r'[a-z0-9]+', text) if len(word) > 1 and word not in STOPWORDS]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


class SearchIndex:
    def __init__(self, documents):
        if not isinstance(documents, list) or not documents:
            raise ValueError('Corpus must be a nonempty list')
        self.documents = []
        ids = set()
        for doc in documents:
            if not isinstance(doc, dict) or any(not isinstance(doc.get(k), str) or not doc[k].strip() for k in ('id', 'title', 'answer')):
                raise ValueError('Each document needs nonempty id, title and answer strings')
            if doc['id'] in ids:
                raise ValueError('Duplicate document id')
            ids.add(doc['id'])
            self.documents.append({k: doc[k] for k in ('id', 'title', 'answer')})
        self.counts = [Counter(tokens(doc['title'] + ' ' + doc['answer'])) for doc in self.documents]
        df = Counter(term for counts in self.counts for term in counts)
        if not df:
            raise ValueError('Corpus has no searchable tokens')
        self.idf = {term: math.log((1 + len(documents)) / (1 + frequency)) + 1 for term, frequency in df.items()}
        self.vectors = [self.vector(counts) for counts in self.counts]

    def vector(self, counts):
        weighted = {term: count * self.idf[term] for term, count in counts.items() if term in self.idf}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        return {term: value / norm for term, value in weighted.items()} if norm else {}

    def rank(self, query, method='tfidf', k=3):
        if method not in METHODS or not isinstance(k, int) or k < 1:
            raise ValueError('Unknown method or invalid k')
        counts = Counter(tokens(query))
        query_vector = self.vector(counts)
        results = []
        for doc, doc_counts, vector in zip(self.documents, self.counts, self.vectors):
            shared = sorted(counts.keys() & doc_counts.keys())
            if method == 'tfidf':
                contributions = {term: query_vector[term] * vector[term] for term in shared}
            else:
                contributions = {term: 1 / len(counts) for term in shared} if counts else {}
            score = min(1.0, sum(contributions.values()))
            if score > 0:
                results.append({**doc, 'score': score, 'matched_terms': shared,
                                'contributions': contributions})
        return sorted(results, key=lambda result: (-result['score'], result['id']))[:k]

    def search(self, query, method='tfidf', threshold=0.2):
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('Threshold must be finite and between 0 and 1')
        candidates = self.rank(query, method)
        accepted = bool(candidates) and candidates[0]['score'] >= threshold
        return {'query': query, 'method': method, 'threshold': threshold,
                'status': 'match' if accepted else 'abstain',
                'answer': candidates[0]['answer'] if accepted else None,
                'source_id': candidates[0]['id'] if accepted else None,
                'candidates': candidates}


def validate_queries(queries, document_ids):
    if not isinstance(queries, list) or not queries:
        raise ValueError('Queries must be a nonempty list')
    ids, texts = set(), set()
    for row in queries:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or not isinstance(row.get('query'), str) or not tokens(row['query']):
            raise ValueError('Each query needs a nonempty id and searchable query')
        if 'relevant_id' not in row or (row['relevant_id'] is not None and row['relevant_id'] not in document_ids):
            raise ValueError('Relevant id must identify a corpus document or be null')
        normalized = tuple(tokens(row['query']))
        if row['id'] in ids or normalized in texts:
            raise ValueError('Duplicate query id or normalized text')
        ids.add(row['id'])
        texts.add(normalized)
    return ids, texts


def assess(index, queries, method, threshold):
    details = []
    correct = answered = answered_correctly = answerable = hits = 0
    reciprocal_sum = 0.0
    for row in queries:
        result = index.search(row['query'], method, threshold)
        expected = row['relevant_id']
        predicted = result['source_id']
        correct += predicted == expected
        answered += predicted is not None
        answered_correctly += predicted is not None and predicted == expected
        if expected is not None:
            answerable += 1
            ranked_ids = [item['id'] for item in result['candidates']]
            hits += bool(ranked_ids) and ranked_ids[0] == expected
            if expected in ranked_ids:
                reciprocal_sum += 1 / (ranked_ids.index(expected) + 1)
        details.append({**row, 'predicted_id': predicted, 'correct': predicted == expected,
                        'top_score': result['candidates'][0]['score'] if result['candidates'] else 0,
                        'ranked_ids': [item['id'] for item in result['candidates']]})
    return {'queries': len(queries), 'answerable_queries': answerable,
            'decision_accuracy': correct / len(queries), 'coverage': answered / len(queries),
            'answered_precision': answered_correctly / answered if answered else None,
            'hit_at_1': hits / answerable if answerable else None,
            'mrr_at_3': reciprocal_sum / answerable if answerable else None,
            'details': details}


def calibrate(index, dev, method):
    # Fixed search grid; tie-break toward more abstention. Never uses test labels.
    options = [(assess(index, dev, method, i / 20)['decision_accuracy'], i / 20) for i in range(21)]
    return max(options)[1]


def evaluate(documents, dev, test):
    index = SearchIndex(documents)
    doc_ids = {doc['id'] for doc in documents}
    dev_ids, dev_texts = validate_queries(dev, doc_ids)
    test_ids, test_texts = validate_queries(test, doc_ids)
    if dev_ids & test_ids or dev_texts & test_texts:
        raise ValueError('Development and test queries must be disjoint')
    report = {'corpus_documents': len(documents), 'dev_queries': len(dev), 'test_queries': len(test),
              'fingerprints': {name: fingerprint(value) for name, value in [('corpus', documents), ('dev', dev), ('test', test)]},
              'methods': {}}
    for method in METHODS:
        threshold = calibrate(index, dev, method)
        report['methods'][method] = {'threshold': threshold,
            'development': assess(index, dev, method, threshold),
            'test': assess(index, test, method, threshold)}
    return report


def report_markdown(report):
    lines = ['# FAQ Retrieval — évaluation', '',
             '> Petit benchmark synthétique pédagogique : aucune mesure de performance en production.', '',
             f"Corpus : {report['corpus_documents']} articles · Réglage : {report['dev_queries']} questions · Test : {report['test_queries']} questions.", '',
             '| Méthode | Seuil réglé sur dev | Hit@1 | MRR@3 | Décisions correctes | Couverture | Précision des réponses |',
             '|---|---:|---:|---:|---:|---:|---:|']
    fmt = lambda value: '—' if value is None else f'{value:.1%}'
    for method, result in report['methods'].items():
        metrics = result['test']
        lines.append(f"| {method} | {result['threshold']:.2f} | " + ' | '.join(fmt(metrics[key]) for key in ['hit_at_1', 'mrr_at_3', 'decision_accuracy', 'coverage', 'answered_precision']) + ' |')
    lines += ['', 'Hit@1 et MRR@3 portent sur les questions avec une réponse dans le corpus, avant abstention. Les autres métriques incluent les questions hors périmètre.', '',
              '## Erreurs observées sur le test', '']
    for method, result in report['methods'].items():
        lines += [f'### {method}', '']
        failures = [row for row in result['test']['details'] if not row['correct']]
        for row in failures:
            lines.append(f"- {row['id']} : {row['query']} — attendu `{row['relevant_id']}`, prédit `{row['predicted_id']}` (score {row['top_score']:.3f}).")
        if not failures:
            lines.append('Aucune erreur sur ce petit jeu synthétique ; cela ne prouve pas une fiabilité générale.')
        lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    search = commands.add_parser('search')
    search.add_argument('query')
    search.add_argument('--corpus', default='data/faq.json')
    search.add_argument('--method', choices=METHODS, default='tfidf')
    search.add_argument('--threshold', type=float, default=0.2, help='Explicit cutoff; default 0.2 is illustrative, not auto-calibrated')
    bench = commands.add_parser('evaluate')
    bench.add_argument('--corpus', default='data/faq.json')
    bench.add_argument('--dev', default='data/dev.json')
    bench.add_argument('--test', default='data/test.json')
    bench.add_argument('--output', default='build')
    args = parser.parse_args()
    try:
        corpus = read_json(args.corpus)
        if args.command == 'search':
            print(json.dumps(SearchIndex(corpus).search(args.query, args.method, args.threshold), ensure_ascii=True, indent=2))
        else:
            report = evaluate(corpus, read_json(args.dev), read_json(args.test))
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=True)
            (output / 'metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            (output / 'report.md').write_text(report_markdown(report), encoding='utf-8')
            print(json.dumps({method: {k: v for k, v in result['test'].items() if k != 'details'} | {'threshold': result['threshold']} for method, result in report['methods'].items()}, indent=2))
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
