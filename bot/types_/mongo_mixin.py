from dataclasses import asdict, fields
from typing import Type, TypeVar, Dict, Any, Optional

T = TypeVar("T", bound="MongoDataclassMixin")


class MongoDataclassMixin:
    _id: Optional[Any] = None

    @classmethod
    def from_dict(
        cls: Type[T],
        data: Dict[str, Any],
    ) -> Optional[T]:
        if not data:
            return None

        item_data = data.copy()
        mongo_id = item_data.pop("_id", None)

        # ignore any fields present in Mongo but not declared on the dataclass
        allowed_fields = {field.name for field in fields(cls)}
        filtered_data = {
            key: value
            for key, value in item_data.items()
            if key in allowed_fields
        }

        item = cls(**filtered_data)  # type: ignore[arg-type]

        if mongo_id is not None:
            item._id = mongo_id

        return item

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        if data.get("_id") is None:
            data.pop("_id", None)

        return data
