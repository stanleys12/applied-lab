# order-book-sim

Limit order book and matching engine with price-time priority (stdlib only).

## Vision
Grow from a minimal matching core into a small market-microstructure lab:
order cancellation, market/IOC orders, a random-flow simulator, and
spread / depth / VWAP analytics.

## Run
    python3 book.py
    python3 sim.py
    python3 test_book.py

## Increments
1. Core book: limit orders, price-time matching, trade at resting price, depth view (done)
2. Market (IOC) orders, order cancellation with lazy heap deletion, unittest suite (done)
3. Seeded random-flow simulator (`sim.py`): limit/market/cancel mix, determinism + uncrossed-book test (done)
4. Analytics (`analytics.py`): spread, mid, microprice, depth imbalance, VWAP, non-mutating impact-cost estimate; wired into sim output (done)
5. Inventory-skewing market maker (`marketmaker.py`) plugged into the simulator via an `agent` hook; fills, cash and mark-to-market PnL, with tests (done)
5. Inventory-skewing market maker (`marketmaker.py`) plugged into the simulator via an `agent` hook; fills, cash and mark-to-market PnL, with tests (done)
