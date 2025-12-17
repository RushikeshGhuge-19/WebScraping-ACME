"""Simple MongoDB storage scaffold for parsed car data.

This module provides a small helper to connect to MongoDB using the
`MONGO_URI`, `MONGO_DB` and `MONGO_COLLECTION` environment variables.
It exposes `save_listing()` which upserts by `url` or `vin` when available.
"""
from typing import Any, Dict, Optional
import os
import time
from functools import wraps

try:
    from pymongo import MongoClient, ASCENDING
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
    from pymongo.write_concern import WriteConcern
except Exception:  # pragma: no cover - dependency may be missing in some envs
    MongoClient = None  # type: ignore
    PyMongoError = Exception  # type: ignore
    ServerSelectionTimeoutError = Exception  # type: ignore

# Configuration via environment
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('MONGO_DB', 'carsdb')
COLLECTION = os.environ.get('MONGO_COLLECTION', 'listings')
# Write concern: w=1 by default, can be 'majority' or integer
MONGO_W = os.environ.get('MONGO_WRITE_CONCERN', '1')
# connection timeouts (seconds)
MONGO_SERVER_SELECTION_TIMEOUT = int(os.environ.get('MONGO_SERVER_SELECTION_TIMEOUT', '5'))

_client: Optional[MongoClient] = None


def _with_retries(retries: int = 3, backoff: float = 0.2):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, retries + 1):
                try:
                    return fn(*args, **kwargs)
                except (PyMongoError, ServerSelectionTimeoutError) as e:
                    last_exc = e
                    time.sleep(backoff * attempt)
            raise last_exc

        return wrapper

    return deco


def get_client() -> MongoClient:
    """Return a cached `MongoClient` configured with sensible timeouts."""
    global _client
    if _client is None:
        if MongoClient is None:
            raise RuntimeError('pymongo is not installed')
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=int(MONGO_SERVER_SELECTION_TIMEOUT * 1000))
    return _client


def get_collection():
    # Apply configured write concern on the collection
    wc = WriteConcern(w=MONGO_W)
    return get_client()[DB_NAME].get_collection(COLLECTION, write_concern=wc)


def ensure_indexes():
    """Create helpful indexes for dedup/upsert operations.

    Creates unique partial indexes on `url` and `vin` when present to
    speed up upserts and avoid duplicates.
    """
    coll = get_client()[DB_NAME][COLLECTION]
    try:
        # unique index on url where url exists
        coll.create_index([('url', ASCENDING)], unique=True, sparse=True, name='uniq_url')
        # unique index on vin where vin exists
        coll.create_index([('vin', ASCENDING)], unique=True, sparse=True, name='uniq_vin')
    except PyMongoError:
        # best-effort: don't raise for index creation failures
        pass


@_with_retries(retries=3, backoff=0.3)
def save_listing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or upsert a single listing document with retries.

    Upsert uses `url` or `vin` as the unique key when present. If neither
    is present the document is inserted as new.
    """
    coll = get_collection()
    if not isinstance(data, dict):
        raise ValueError('data must be a dict')

    filterq: Dict[str, Any] = {}
    if data.get('url'):
        filterq = {'url': data.get('url')}
    elif data.get('vin'):
        filterq = {'vin': data.get('vin')}

    try:
        if filterq:
            res = coll.update_one(filterq, {'$set': data}, upsert=True)
            return {
                'matched_count': int(res.matched_count),
                'modified_count': int(res.modified_count),
                'upserted_id': str(res.upserted_id) if res.upserted_id else None,
            }
        else:
            res = coll.insert_one(data)
            return {'inserted_id': str(res.inserted_id)}
    except PyMongoError as e:
        return {'error': str(e)}


def close_client():
    global _client
    if _client:
        try:
            _client.close()
        finally:
            _client = None

