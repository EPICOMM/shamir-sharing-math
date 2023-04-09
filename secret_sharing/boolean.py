from copy import copy
from enum import Enum
from typing import Any


__all__ = ("NodeKind", "BooleanNode")


class NodeKind(Enum):
    AND = "&"
    OR = "|"
    VAR = "_"
    THRESHOLD = "T"


class BooleanNode:
    def __init__(
        self,
        kind: NodeKind,
        children: list["BooleanNode"] = None,
        name: Any = None,
        threshold: int = None,
    ):
        if children is not None and kind == NodeKind.VAR:
            raise ValueError("`children` are not compatible with `NodeKind.VAR`")
        if name is not None and kind != NodeKind.VAR:
            raise ValueError("`name` is only compatible with `NodeKind.VAR`")
        if threshold is not None and kind != NodeKind.THRESHOLD:
            raise ValueError("`threshold` is only compatible with `NodeKind.THRESHOLD`")

        if kind != NodeKind.VAR and children is None:
            raise ValueError(f"`children` is required for `{kind}`")
        if kind == NodeKind.THRESHOLD and threshold is None:
            raise ValueError("`threshold` is required for `NodeKind.THRESHOLD`")

        self._kind = kind
        self._children = children or []
        self._name = name
        self._threshold = threshold
        self._variables = None  # cached

    @classmethod
    def or_(cls, *children: list["BooleanNode"]) -> "BooleanNode":
        if len(children) == 1:
            return children[0]
        return cls(kind=NodeKind.OR, children=children)

    @classmethod
    def and_(cls, *children: list["BooleanNode"]) -> "BooleanNode":
        if len(children) == 1:
            return children[0]
        return cls(kind=NodeKind.AND, children=children)

    @classmethod
    def var(cls, name: str) -> "BooleanNode":
        return cls(kind=NodeKind.VAR, name=name)

    @classmethod
    def thresh(cls, threshold: int, *children: list["BooleanNode"]) -> "BooleanNode":
        return cls(kind=NodeKind.THRESHOLD, threshold=threshold, children=children)

    @property
    def kind(self) -> NodeKind:
        return self._kind

    @property
    def children(self) -> list["BooleanNode"]:
        if self._kind == NodeKind.VAR:
            raise ValueError("variables have no children")
        return self._children

    @property
    def name(self) -> Any:
        if self._kind != NodeKind.VAR:
            raise ValueError("only variables have names")
        return self._name

    @property
    def threshold(self) -> int:
        if self._kind != NodeKind.THRESHOLD:
            raise ValueError("only THRESHOLD have threshold")
        return self._threshold

    def __str__(self) -> str:
        if self.kind == NodeKind.VAR:
            return f'`{self.name}`'
        elif self.kind == NodeKind.THRESHOLD:
            return f'T{self.threshold}({", ".join(str(i) for i in self.children)})'
        elif self.kind == NodeKind.AND:
            return f'({" & ".join(str(i) for i in self.children)})'
        elif self.kind == NodeKind.OR:
            return f'({" | ".join(str(i) for i in self.children)})'

    def walk(self, f) -> "BooleanNode":
        res = f(copy(self))
        if res._children:
            res._children = [child.walk(f) for child in res.children]
        return res
