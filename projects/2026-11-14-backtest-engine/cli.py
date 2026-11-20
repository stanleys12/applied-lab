"""One-shot CLI report: strategy vs buy&hold, optional vol targeting, Sharpe bootstrap CI.

    python3 cli.py --n 1000 --seed 5 --fast 10 --slow 30 --vol-target 0.10 --cost-bps 5
"""
import argparse
from backtest import gbm_prices, sma_crossover, buy_and_hold, run_backtest, metrics, report
from bootstrap import sharpe_ci
from sizing import vol_target, check_no_lookahead


def main(argv=None):
    ap = argparse.ArgumentParser(description="backtest-engine report")
    ap.add_argument("--n", type=int, default=756, help="number of bars")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mu", type=float, default=0.08, help="annual drift of the GBM")
    ap.add_argument("--sigma", type=float, default=0.2, help="annual vol of the GBM")
    ap.add_argument("--fast", type=int, default=10)
    ap.add_argument("--slow", type=int, default=30)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--vol-target", type=float, default=None, help="annual vol target, e.g. 0.10")
    ap.add_argument("--boot", type=int, default=500, help="bootstrap resamples")
    args = ap.parse_args(argv)
    if args.fast >= args.slow:
        ap.error("--fast must be < --slow")
    if args.n < args.slow + 2:
        ap.error("--n must exceed --slow by at least 2")

    prices = gbm_prices(args.n, mu=args.mu, sigma=args.sigma, seed=args.seed)
    sig = sma_crossover(prices, args.fast, args.slow)
    strategies = [("buy&hold", buy_and_hold(prices)), ("sma %d/%d" % (args.fast, args.slow), sig)]
    if args.vol_target:
        strategies.append(("vol-tgt %g" % args.vol_target, vol_target(prices, sig, target_vol=args.vol_target)))

    print("GBM n=%d seed=%d mu=%g sigma=%g cost=%gbps  look-ahead check: %s" % (
        args.n, args.seed, args.mu, args.sigma, args.cost_bps, "ok" if check_no_lookahead() else "FAIL"))
    for name, s in strategies:
        rets, eq = run_backtest(prices, s, args.cost_bps)
        report(name, metrics(rets, eq))
        pt, lo, hi, p0 = sharpe_ci(rets, n_boot=args.boot)
        print("%-14s   95%% CI sharpe [%5.2f, %5.2f]  P(sharpe<=0)=%.2f" % ("", lo, hi, p0))


if __name__ == "__main__":
    main()
