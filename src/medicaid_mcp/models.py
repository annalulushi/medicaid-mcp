"""Typed result shapes for structured tool output.

Step 5. Dataset ids are `identifier`, not `id`. `/api/1/search` results are an object
keyed by URI when there are hits but `[]` when there are none, so shaping handles both.
"""
