"""In-memory TTL cache: search 15 min, metadata 1 hour, rows never.

Step 5. Takes an injectable clock so expiry is testable without `sleep`.
"""
