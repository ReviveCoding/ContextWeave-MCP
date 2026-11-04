from __future__ import annotations

import math

import numpy as np
import pytest

from contextweave.retrieval import BM25, _tokens


@pytest.mark.parametrize("texts", [[], ["", ""], ["alpha alpha", "beta", "", "alpha beta"]])
@pytest.mark.parametrize("query", ["", "missing", "alpha alpha beta"])
def test_postings_preserve_bm25_scores(texts, query):
    model = BM25(texts)
    expected = np.zeros(len(texts), dtype=np.float32)
    for term in set(_tokens(query)):
        frequency = model.document_frequency[term]
        if not frequency:
            continue
        inverse_frequency = math.log(1 + (model.n - frequency + 0.5) / (frequency + 0.5))
        for index, counts in enumerate(model.term_counts):
            count = counts[term]
            if count:
                norm = model.k1 * (1 - model.b + model.b * model.lengths[index] / model.avg_length)
                expected[index] += inverse_frequency * count * (model.k1 + 1) / (count + norm)
    np.testing.assert_array_equal(model.scores(query), expected)
