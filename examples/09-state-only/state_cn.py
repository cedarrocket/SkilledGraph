from operator import add
from typing import Annotated

from typing_extensions import TypedDict


class State(TypedDict):
    value: int
    events: Annotated[list[str], add]
