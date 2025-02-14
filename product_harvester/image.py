from typing import NamedTuple


class Image(NamedTuple):
    id: str
    data: str

    def __str__(self) -> str:
        return self.data

    def __repr__(self) -> str:
        return self.id
