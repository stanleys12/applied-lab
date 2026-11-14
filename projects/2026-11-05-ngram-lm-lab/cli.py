"""CLI for ngram-lm-lab: evaluate every model on a text file (one line = one document), or sample.

    python3 cli.py eval corpus.txt --max-n 5 --folds 3
    python3 cli.py sample corpus.txt -n 3 --count 5 --seed 1
"""
import argparse
import random
import statistics
import sys

from ngram_lm import CORPUS, InterpolatedLM, KneserNeyLM, NGramLM


def read_lines(path):
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    lines = [l.strip() for l in lines if l.strip()]
    if not lines:
        raise SystemExit("no non-empty lines in input")
    return lines


def kfold(docs, folds, seed):
    """Yield (train, test) splits over shuffled docs; every doc is tested exactly once."""
    if not 2 <= folds <= len(docs):
        raise SystemExit("--folds must be between 2 and the number of lines (%d)" % len(docs))
    docs = docs[:]
    random.Random(seed).shuffle(docs)
    for i in range(folds):
        test = docs[i::folds]
        train = [d for j, d in enumerate(docs) if j % folds != i]
        yield train, test


def _em(n, train):
    # Fitting lambdas on events already in the counts would overfit, so hold out every 4th
    # doc: train on the rest, then fit the lambdas on that held-out quarter.
    dev = train[::4] or train
    rest = [d for i, d in enumerate(train) if i % 4] or train
    lm = InterpolatedLM(n).train(rest)
    lm.fit_lambdas(dev)
    return lm


MAKERS = {
    "add-k": lambda n, tr: NGramLM(n).train(tr),
    "interp": lambda n, tr: InterpolatedLM(n).train(tr),
    "interp+EM": _em,
    "kneser-ney": lambda n, tr: KneserNeyLM(n).train(tr),
}


def evaluate(docs, max_n, folds, seed):
    """Held-out perplexity lists (one value per fold) for each (model, n)."""
    results = {name: {n: [] for n in range(1, max_n + 1)} for name in MAKERS}
    for train, test in kfold(docs, folds, seed):
        for name, make in MAKERS.items():
            for n in range(1, max_n + 1):
                results[name][n].append(make(n, train).perplexity(test))
    return results


def print_table(results, max_n):
    print("%-12s" % "model" + "".join("%14s" % ("n=%d" % n) for n in range(1, max_n + 1)))
    for name, by_n in results.items():
        row = ""
        for n in range(1, max_n + 1):
            v = by_n[n]
            sd = statistics.stdev(v) if len(v) > 1 else 0.0
            row += "%14s" % ("%.2f±%.2f" % (statistics.mean(v), sd))
        print("%-12s%s" % (name, row))
    best = min((statistics.mean(v), name, n) for name, by_n in results.items() for n, v in by_n.items())
    print("best: %s n=%d (mean ppl %.2f)" % (best[1], best[2], best[0]))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval", help="k-fold perplexity comparison of all models")
    e.add_argument("path", nargs="?", default=None, help="text file, '-' for stdin (default: built-in corpus)")
    e.add_argument("--max-n", type=int, default=4)
    e.add_argument("--folds", type=int, default=3)
    e.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("sample", help="train on a file and sample new lines")
    s.add_argument("path", nargs="?", default=None)
    s.add_argument("-n", type=int, default=3)
    s.add_argument("--count", type=int, default=5)
    s.add_argument("--seed", type=int, default=None)
    a = p.parse_args(argv)
    docs = read_lines(a.path) if a.path else list(CORPUS)
    if a.cmd == "eval":
        print("%d docs, %d-fold CV" % (len(docs), a.folds))
        print_table(evaluate(docs, a.max_n, a.folds, a.seed), a.max_n)
    else:
        lm = NGramLM(a.n).train(docs)
        rng = random.Random(a.seed)
        for _ in range(a.count):
            print(lm.sample(rng))


if __name__ == "__main__":
    main()
