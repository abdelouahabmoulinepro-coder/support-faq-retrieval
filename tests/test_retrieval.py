import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from retrieval import SearchIndex, assess, calibrate, evaluate, fingerprint, read_json, tokens


DOCS = [
    {'id': 'a', 'title': 'pomme', 'answer': 'poire'},
    {'id': 'b', 'title': 'pomme', 'answer': 'banane'},
]


class RetrievalTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(tokens('Où télécharger les FACTURES ?'), ['telecharger', 'factures'])

    def test_tfidf_hand_calculation(self):
        index = SearchIndex(DOCS)
        rare_idf = math.log(3 / 2) + 1
        self.assertAlmostEqual(index.idf['poire'], rare_idf)
        self.assertAlmostEqual(index.idf['pomme'], 1)
        result = index.rank('poire')[0]
        self.assertEqual(result['id'], 'a')
        self.assertAlmostEqual(result['score'], rare_idf / math.sqrt(1 + rare_idf**2))
        self.assertAlmostEqual(sum(result['contributions'].values()), result['score'])

    def test_overlap_baseline_counts_unique_terms(self):
        result = SearchIndex(DOCS).rank('poire poire mystere', 'overlap')[0]
        self.assertAlmostEqual(result['score'], .5)

    def test_empty_and_unknown_queries_abstain(self):
        for query in ['', 'le la les', 'astronaute']:
            for method in ('tfidf', 'overlap'):
                self.assertEqual(SearchIndex(DOCS).search(query, method, 0)['status'], 'abstain')

    def test_tie_breaks_by_id(self):
        self.assertEqual([item['id'] for item in SearchIndex(list(reversed(DOCS))).rank('pomme')], ['a', 'b'])

    def test_threshold_boundary(self):
        index = SearchIndex(DOCS)
        score = index.rank('poire')[0]['score']
        self.assertEqual(index.search('poire', threshold=score)['source_id'], 'a')
        self.assertIsNone(index.search('poire', threshold=score + .001)['source_id'])
        for bad in [-1, 1.1, math.nan, math.inf]:
            with self.assertRaises(ValueError):
                index.search('poire', threshold=bad)

    def test_answer_is_verbatim_and_sourced(self):
        result = SearchIndex(DOCS).search('poire')
        self.assertEqual(result['answer'], DOCS[0]['answer'])
        self.assertEqual(result['source_id'], 'a')

    def test_search_does_not_fit_on_query(self):
        index = SearchIndex(DOCS)
        previous = dict(index.idf)
        index.search('poire astronaute astronaute')
        self.assertEqual(index.idf, previous)
        self.assertNotIn('astronaute', index.idf)

    def test_invalid_corpus(self):
        for corpus in [[], [DOCS[0], DOCS[0]], [{'id': 'a', 'title': '', 'answer': 'x'}]]:
            with self.assertRaises(ValueError):
                SearchIndex(corpus)

    def test_metrics_known_fixture(self):
        queries = [{'id': '1', 'query': 'poire', 'relevant_id': 'a'},
                   {'id': '2', 'query': 'astronaute', 'relevant_id': None},
                   {'id': '3', 'query': 'banane', 'relevant_id': 'a'}]
        metrics = assess(SearchIndex(DOCS), queries, 'tfidf', .2)
        self.assertAlmostEqual(metrics['decision_accuracy'], 2/3)
        self.assertAlmostEqual(metrics['coverage'], 2/3)
        self.assertAlmostEqual(metrics['answered_precision'], .5)
        self.assertAlmostEqual(metrics['hit_at_1'], .5)
        self.assertAlmostEqual(metrics['mrr_at_3'], .5)

    def test_split_overlap_rejected(self):
        dev = [{'id': 'd', 'query': 'poire', 'relevant_id': 'a'}]
        with self.assertRaises(ValueError):
            evaluate(DOCS, dev, [{'id': 't', 'query': 'POIRE', 'relevant_id': 'a'}])

    def test_threshold_independent_of_test_labels(self):
        dev = [{'id': 'd', 'query': 'poire', 'relevant_id': 'a'}]
        test = [{'id': 't', 'query': 'banane', 'relevant_id': 'b'}]
        first = evaluate(DOCS, dev, test)
        second = evaluate(DOCS, dev, [{**test[0], 'relevant_id': None}])
        for method in ('tfidf', 'overlap'):
            self.assertEqual(first['methods'][method]['threshold'], second['methods'][method]['threshold'])

    def test_unknown_label_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(DOCS, [{'id': 'd', 'query': 'poire', 'relevant_id': 'missing'}],
                     [{'id': 't', 'query': 'banane', 'relevant_id': 'b'}])

    def test_cli_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, 'retrieval.py', 'evaluate', '--output', folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = read_json(Path(folder) / 'metrics.json')
            self.assertEqual(report['corpus_documents'], 12)
            self.assertEqual(report['test_queries'], 30)
            self.assertEqual(report['fingerprints']['corpus'], fingerprint(read_json('data/faq.json')))
            self.assertIn('Erreurs', (Path(folder) / 'report.md').read_text(encoding='utf-8'))
        result = subprocess.run([sys.executable, 'retrieval.py', 'search', 'astronaute'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(json.loads(result.stdout)['answer'])


if __name__ == '__main__':
    unittest.main()
