from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.firebase import get_firestore_client

T = TypeVar("T", bound=BaseModel)

class FirestoreService(Generic[T]):
    """Base service for Firestore CRUD operations."""

    def __init__(self, collection_name: str, model_class: Type[T]):
        self.db = get_firestore_client()
        self.collection = self.db.collection(collection_name)
        self.model_class = model_class

    def _to_model(self, doc: Any) -> Optional[T]:
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return self.model_class(**data)

    async def create(self, data: T) -> T:
        """Create a new document."""
        doc_data = data.model_dump(exclude={"id"})
        doc_id = getattr(data, 'id', None)
        doc_ref = self.collection.document(doc_id if doc_id else None)
        await doc_ref.set(doc_data)
        data.id = doc_ref.id
        return data

    async def get(self, doc_id: str) -> Optional[T]:
        """Get a document by ID."""
        doc_ref = self.collection.document(doc_id)
        doc = await doc_ref.get()
        return self._to_model(doc)

    async def update(self, doc_id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a document."""
        doc_ref = self.collection.document(doc_id)
        await doc_ref.update(data)
        return await self.get(doc_id)

    async def delete(self, doc_id: str) -> None:
        """Delete a document."""
        await self.collection.document(doc_id).delete()

    async def list(self, filters: List[tuple] = None, order_by: str = None, limit: int = 100) -> List[T]:
        """List documents with optional filters."""
        query = self.collection
        if filters:
            for field, op, value in filters:
                query = query.where(filter=FieldFilter(field, op, value))

        if order_by:
            query = query.order_by(order_by)

        docs = query.limit(limit).stream()
        results = []
        async for doc in docs:
            results.append(self._to_model(doc))
        return [r for r in results if r is not None]

# Specific services will be implemented in their own files or here if small
