# backtest-engine

A small, honest backtester in pure stdlib. The point is to get the *details* right —
look-ahead safety, transaction costs, and metrics — and to show how easily a strategy
looks good on noise.

## Vision
Synthetic GBM prices + SMA-crossover -> position sizing & costs -> walk-forward / parameter
sweep that demonstrates overfitting -> bootstrap confidence intervals on Sharpe -> CLI report.

## Run
    python3 backtest.py   # baseline report
    python3 sweep.py      # overfitting demo

## Increments
1. GBM generator, SMA crossover, look-ahead-safe backtest loop with bps costs, metrics (return, CAGR, vol, Sharpe, max drawdown) (done)
2. `sweep.py`: SMA grid search + train/test split; on driftless GBM the best in-sample Sharpe (~0.77) collapses out-of-sample (~-0.10) (done)
