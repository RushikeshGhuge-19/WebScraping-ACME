"""Simple MongoDB storage scaffold for parsed car data.

This module provides a small helper to connect to MongoDB using the
`MONGO_URI`, `MONGO_DB` and `MONGO_COLLECTION` environment variables.
It exposes `save_listing()` which upserts by `url` or `vin` when available.
"""
from typing import Any, Dict, Optional
import os

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except Exception:  # pragma: no cover - dependency may be missing in some envs
    MongoClient = None  # type: ignore
    PyMongoError = Exception  # type: ignore

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('MONGO_DB', 'carsdb')
COLLECTION = os.environ.get('MONGO_COLLECTION', 'listings')

_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        if MongoClient is None:
            raise RuntimeError('pymongo is not installed')
        _client = MongoClient(MONGO_URI)
    return _client


def get_collection():
    return get_client()[DB_NAME][COLLECTION]


def save_listing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or upsert a single listing document.

    If `url` exists in `data` it will be used as the unique key. If not,
    `vin` will be used. Otherwise the document is inserted as new.

    Returns a small dict with operation result information.
    """
    coll = get_collection()
    # normalise a few trivial types
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
