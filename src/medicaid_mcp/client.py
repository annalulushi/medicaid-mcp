"""DKAN API client: HTTP only.

Step 4. Returns parsed JSON or raises `ApiTimeout` / `ApiHttpError` / `ApiPayloadError`.
Metastore requests always send `?show-reference-ids`. Never returns an empty result where
an error occurred.
"""
