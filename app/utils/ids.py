from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class PyObjectId:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls._validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.no_info_plain_validator_function(cls._from_str),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def _validate(cls, v: Any, handler: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId: {v}")

    @classmethod
    def _from_str(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId string: {v}")

    @classmethod
    def _serialize(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)


def to_obj_id(value: Any) -> Optional[ObjectId]:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return None


def safe_oid(value: Any) -> Optional[str]:
    oid = to_obj_id(value)
    return str(oid) if oid else None


def add_id_field(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc is None:
        return None
    if "_id" in doc and "id" not in doc:
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
    return doc
