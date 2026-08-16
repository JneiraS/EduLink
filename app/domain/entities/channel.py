from dataclasses import dataclass


@dataclass(slots=True)
class Channel:
    id: int | None
    name: str
    created_by: int
    kind: str = "group"
