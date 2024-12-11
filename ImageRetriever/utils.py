def aggregate_rankings(rankers_results, weights, k):
    scores = {}
    for i, R_i in enumerate(rankers_results):
        for j, result in enumerate(R_i):
            if result not in scores:
                scores[result] = 0
            scores[result] += weights[i] * (1 / (j + 1))

    ranked_results = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return ranked_results[:k]
