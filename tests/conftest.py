from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import MagicMock

from bson import ObjectId
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.constants.roles import UserRole
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.collections import (
    AUDIT_LOGS,
    CONVERSATIONS,
    DEPARTMENTS,
    FAQS,
    FEEDBACK,
    KNOWLEDGE_BASE,
    MESSAGES,
    NOTIFICATIONS,
    TICKETS,
    USERS,
)
from app.dependencies.database import get_db
from app.main import app
from app.models.user import new_user_doc
from app.utils.ids import to_obj_id


class AsyncCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = list(docs)

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self._docs.sort(
                    key=lambda x: (x.get(k) is None, x.get(k)),
                    reverse=(d == -1 or str(d).lower() == "desc"),
                )
        else:
            self._docs.sort(
                key=lambda x: (x.get(key_or_list) is None, x.get(key_or_list)),
                reverse=(direction == -1),
            )
        return self

    def limit(self, n: int):
        if n is not None:
            self._docs = self._docs[:n]
        return self

    def skip(self, n: int):
        if n is not None:
            self._docs = self._docs[n:]
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])

    def __iter__(self):
        return iter(self._docs)


def _match_condition(val: Any, cond: Any) -> bool:
    if isinstance(cond, dict):
        for op, target in cond.items():
            if op == "$in":
                target_strs = {str(t) if isinstance(t, ObjectId) else t for t in target}
                val_cmp = str(val) if isinstance(val, ObjectId) else val
                if val_cmp not in target_strs and val not in target:
                    return False
            elif op == "$ne":
                if str(val) == str(target):
                    return False
            elif op == "$exists":
                exists = val is not None
                if exists != bool(target):
                    return False
            elif op == "$gte":
                if val is None or val < target:
                    return False
            elif op == "$lte":
                if val is None or val > target:
                    return False
            elif op == "$gt":
                if val is None or val <= target:
                    return False
            elif op == "$lt":
                if val is None or val >= target:
                    return False
        return True
    if isinstance(cond, ObjectId) or isinstance(val, ObjectId):
        return str(val) == str(cond)
    return val == cond


def _doc_matches(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    if not query:
        return True
    if "$or" in query:
        or_branches = query["$or"]
        matched_or = False
        for branch in or_branches:
            if _doc_matches(doc, branch):
                matched_or = True
                break
        if not matched_or:
            return False

    for k, v in query.items():
        if k == "$or":
            continue
        doc_val = doc.get(k)
        if not _match_condition(doc_val, v):
            return False
    return True


class MockAsyncCollection:
    def __init__(self, name: str):
        self.name = name
        self.docs: List[Dict[str, Any]] = []

    async def insert_one(self, doc: Dict[str, Any]):
        new_doc = dict(doc)
        if "_id" not in new_doc or new_doc["_id"] is None:
            new_doc["_id"] = ObjectId()
        self.docs.append(new_doc)
        res = MagicMock()
        res.inserted_id = new_doc["_id"]
        return res

    async def find_one(self, query: Optional[Dict[str, Any]] = None, projection: Any = None, sort: Any = None):
        query = query or {}
        matched = [dict(d) for d in self.docs if _doc_matches(d, query)]
        if sort:
            cursor = AsyncCursor(matched)
            cursor.sort(sort)
            matched = cursor._docs
        return matched[0] if matched else None

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Any = None):
        query = query or {}
        matched = [dict(d) for d in self.docs if _doc_matches(d, query)]
        return AsyncCursor(matched)

    async def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        query = query or {}
        return sum(1 for d in self.docs if _doc_matches(d, query))

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        for d in self.docs:
            if _doc_matches(d, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        d[k] = v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        lst = d.setdefault(k, [])
                        if isinstance(v, dict) and "$each" in v:
                            lst.extend(v["$each"])
                        else:
                            lst.append(v)
                if "$pull" in update:
                    for k, v in update["$pull"].items():
                        if k in d and isinstance(d[k], list):
                            d[k] = [item for item in d[k] if item != v]
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        modified = 0
        for d in self.docs:
            if _doc_matches(d, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        d[k] = v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        lst = d.setdefault(k, [])
                        if isinstance(v, dict) and "$each" in v:
                            lst.extend(v["$each"])
                        else:
                            lst.append(v)
                if "$pull" in update:
                    for k, v in update["$pull"].items():
                        if k in d and isinstance(d[k], list):
                            d[k] = [item for item in d[k] if item != v]
                modified += 1
        res = MagicMock()
        res.modified_count = modified
        return res

    async def find_one_and_update(
        self, query: Dict[str, Any], update: Dict[str, Any], return_document: bool = True
    ):
        for d in self.docs:
            if _doc_matches(d, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        d[k] = v
                return dict(d)
        return None

    async def delete_one(self, query: Dict[str, Any]):
        for i, d in enumerate(self.docs):
            if _doc_matches(d, query):
                del self.docs[i]
                res = MagicMock()
                res.deleted_count = 1
                return res
        res = MagicMock()
        res.deleted_count = 0
        return res

    async def delete_many(self, query: Dict[str, Any]):
        initial = len(self.docs)
        self.docs = [d for d in self.docs if not _doc_matches(d, query)]
        res = MagicMock()
        res.deleted_count = initial - len(self.docs)
        return res

    def aggregate(self, pipeline: List[Dict[str, Any]]):
        res = [dict(d) for d in self.docs]
        for stage in pipeline:
            if "$match" in stage:
                res = [d for d in res if _doc_matches(d, stage["$match"])]
            elif "$limit" in stage:
                res = res[:stage["$limit"]]
            elif "$sort" in stage:
                for k, direction in reversed(list(stage["$sort"].items())):
                    res.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=(direction == -1))
        return AsyncCursor(res)

    async def create_index(self, keys, **kwargs):
        return kwargs.get("name", "idx")


class MockAsyncDatabase:
    def __init__(self):
        self._collections: Dict[str, MockAsyncCollection] = {}

    def __getitem__(self, name: str) -> MockAsyncCollection:
        if name not in self._collections:
            self._collections[name] = MockAsyncCollection(name)
        return self._collections[name]

    def clear_all(self):
        for col in self._collections.values():
            col.docs.clear()


from app.ai.llm_client import BaseLLMClient
import app.ai.llm_client as llm_mod


class MockTestLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs) -> str:
        return "To register for semester courses, log in to the Student Portal and select your approved courses."

    async def generate_structured(self, prompt: str, **kwargs) -> Dict[str, Any]:
        return {
            "intent": "course_registration",
            "category": "course_registration",
            "confidence": 0.95,
            "requires_knowledge_search": True,
            "requires_human": False,
        }


@pytest.fixture(autouse=True)
def mock_llm_client_fixture(monkeypatch):
    monkeypatch.setattr(llm_mod, "_llm_client", MockTestLLMClient())


@pytest.fixture(scope="session")
def test_db():
    return MockAsyncDatabase()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(test_db):
    test_db.clear_all()
    app.dependency_overrides[get_db] = lambda: test_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def student_user(test_db) -> Dict[str, Any]:
    doc = new_user_doc(
        name="Student User",
        email="student@demo.institution.edu",
        password_hash=hash_password("Password123!"),
        role=UserRole.STUDENT.value,
        matric_number="CSC/2026/001",
        faculty="Physical Sciences",
    )
    res = await test_db[USERS].insert_one(doc)
    user_id = str(res.inserted_id)
    token = create_access_token(subject=user_id, role=UserRole.STUDENT.value)
    return {
        "id": user_id,
        "name": doc["name"],
        "email": doc["email"],
        "role": UserRole.STUDENT.value,
        "token": token,
        "headers": auth_headers(token),
    }


@pytest_asyncio.fixture
async def staff_user(test_db) -> Dict[str, Any]:
    dept_doc = {
        "name": "Computer Science",
        "code": "CSC",
        "faculty": "Physical Sciences",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    dept_res = await test_db[DEPARTMENTS].insert_one(dept_doc)
    dept_id = dept_res.inserted_id

    doc = new_user_doc(
        name="Staff Member",
        email="staff@demo.institution.edu",
        password_hash=hash_password("Password123!"),
        role=UserRole.STAFF.value,
        department_id=dept_id,
        faculty="Physical Sciences",
    )
    res = await test_db[USERS].insert_one(doc)
    user_id = str(res.inserted_id)
    token = create_access_token(subject=user_id, role=UserRole.STAFF.value)
    return {
        "id": user_id,
        "name": doc["name"],
        "email": doc["email"],
        "role": UserRole.STAFF.value,
        "department_id": str(dept_id),
        "token": token,
        "headers": auth_headers(token),
    }


@pytest_asyncio.fixture
async def admin_user(test_db) -> Dict[str, Any]:
    doc = new_user_doc(
        name="Admin User",
        email="admin@demo.institution.edu",
        password_hash=hash_password("Password123!"),
        role=UserRole.ADMIN.value,
    )
    res = await test_db[USERS].insert_one(doc)
    user_id = str(res.inserted_id)
    token = create_access_token(subject=user_id, role=UserRole.ADMIN.value)
    return {
        "id": user_id,
        "name": doc["name"],
        "email": doc["email"],
        "role": UserRole.ADMIN.value,
        "token": token,
        "headers": auth_headers(token),
    }


@pytest_asyncio.fixture
async def super_admin_user(test_db) -> Dict[str, Any]:
    doc = new_user_doc(
        name="Super Admin",
        email="superadmin@demo.institution.edu",
        password_hash=hash_password("Password123!"),
        role=UserRole.SUPER_ADMIN.value,
    )
    res = await test_db[USERS].insert_one(doc)
    user_id = str(res.inserted_id)
    token = create_access_token(subject=user_id, role=UserRole.SUPER_ADMIN.value)
    return {
        "id": user_id,
        "name": doc["name"],
        "email": doc["email"],
        "role": UserRole.SUPER_ADMIN.value,
        "token": token,
        "headers": auth_headers(token),
    }
