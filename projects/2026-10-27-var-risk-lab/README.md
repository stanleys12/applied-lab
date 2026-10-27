# var-risk-lab

Market-risk measurement from scratch in stdlib Python: Value-at-Risk and Expected Shortfall.

## Vision
Compare historical, parametric and Monte Carlo VaR on fat-tailed returns, then
backtest them (Kupiec / Basel traffic-light exceedance tests) and extend to
multi-asset portfolios with a covariance matrix.

## Run
    python3 var.py                      # synthetic fat-tailed series
    python3 var.py -0.012 0.004 ...     # your own daily returns
    python3 -m unittest

## Increments
1. Historical and parametric VaR/CVaR, synthetic fat-tailed returns, report CLI (done)
