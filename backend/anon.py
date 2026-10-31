"""Anonymous-query ownership without storing who asked.

The queries table keeps only HMAC(secret, user_id + query_id). The server can still answer "is the current
user the author of this query?" (recompute and compare) but a copy of the database alone does not say who asked.
Set ANON_SECRET (falls back to JWT_SECRET) and never change it, or authors lose their 'Resolve' button.
"""
import hashlib
import hmac
import os


def _key() -> bytes:
    return (os.environ.get("ANON_SECRET") or os.environ.get("JWT_SECRET") or "aura_campus_secret_change_me").encode()


def author_proof(user_id, query_id) -> str:
    return hmac.new(_key(), f"query:{int(user_id)}:{int(query_id)}".encode(), hashlib.sha256).hexdigest()


def is_author(user_id, query_id, proof) -> bool:
    if not proof or user_id is None:
        return False
    return hmac.compare_digest(author_proof(user_id, query_id), proof)
