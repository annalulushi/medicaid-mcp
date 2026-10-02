"""Friendly filter DSL -> DKAN query JSON. Pure translation: no network, no state.

Step 3. Imports nothing from `client`. Rejects `limit < 1` or `> 500` (never clamps), and
casts or refuses numeric ops on `text`-typed columns rather than comparing lexically.
"""
