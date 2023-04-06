from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from .boolean import BooleanNode, NodeKind
import random

T = TypeVar("T")


@dataclass
class Part:
    name: str
    values: list[int]


@dataclass(frozen=True)
class Slice(Generic[T]):
    values: list[T]
    start: int = 0

    @property
    def head(self) -> T | None:
        if self.start >= len(self.values):
            return None
        return self.values[self.start]

    def move(self) -> "Slice[T]":
        return Slice(self.values, self.start + 1)


class Scheme(Enum):
    SHAMIR = "shamir"
    COMPLEX = "complex"


@dataclass(kw_only=True)
class Configuration:
    scheme: Scheme
    modulo: int
    formula: str
    version: int = 1

    def make_formula(self) -> BooleanNode:
        formula: BooleanNode = self.formula  # TODO: parse it
        counter = Counter()
        def walker(node: BooleanNode):
            if node.kind == NodeKind.VAR:
                counter[node.name] = counter[node.name] + 1
                node = BooleanNode.var((node.name, counter[node.name]))
            return node
        return formula.walk(walker)
    
    def split(self, secret: int) -> list[Part]:
        formula = self.make_formula()
        secret %= self.modulo
        splitted = Splitter(self).split(secret, formula)
        splitted.sort(key=lambda x: x[0][1])
        result = {}
        for key, val in splitted:
            name, idx = key
            if name not in result:
                result[name] = Part(name, [])
            assert idx - 1 == len(result[name].values)
            result[name].values.append(val)
        return list(result.values())
    
    def restore(self, parts: list[Part]) -> int | None:
        formula = self.make_formula()
        vals = {}
        for part in parts:
            for idx, val in enumerate(part.values, 1):
                vals[(part.name, idx)] = val
        return Restorer(self, vals).restore(formula)


class MathBase:
    def __init__(self, conf: Configuration) -> None:
        self.conf = conf

    @property
    def mod(self) -> int:
        return self.conf.modulo

    def rand(self, n) -> list[int]:
        return [random.randint(0, self.mod - 1) for _ in range(n)]

    def inv(self, n: int) -> int:
        n = n % self.mod
        m = self.mod
        m0 = self.mod
        y = 0
        x = 1

        while n > 1:
            # q is quotient
            q = n // m

            t = m

            # m is remainder now, process
            # same as Euclid's algo
            m = n % m
            n = t
            t = y

            # Update x and y
            y = x - q * y
            x = t

        # Make x positive
        if x < 0:
            x = x + m0

        return x


class Splitter(MathBase):
    def _split_threshold(self, secret: int, f: BooleanNode) -> list[tuple[Any, int]]:
        if f.kind != NodeKind.THRESHOLD:
            return self.split(secret, f)

        k = f.threshold
        poly = [secret] + self.rand(k - 1)

        def evaluate(x):
            res = 0
            xpow = 1
            for i in poly:
                res += i * xpow
                res %= self.mod
                xpow *= x
                xpow %= self.mod
            return res
        
        assert evaluate(0) == secret

        result = []
        for n, child in enumerate(f.children, 1):
            s = evaluate(n)
            result.extend(self.split(s, child))
        return result

    def split(self, secret: int, f: BooleanNode) -> list[tuple[Any, int]]:
        if f.kind == NodeKind.VAR:
            return [(f.name, secret)]
        if f.kind == NodeKind.THRESHOLD:
            return self._split_threshold(secret, f)
        if f.kind == NodeKind.OR:
            result = []
            for child in f.children:
                result.extend(self.split(secret, child))
            return result
        if f.kind == NodeKind.AND:
            parts = self.rand(len(f.children) - 1)
            parts.append((secret - sum(parts)) % self.mod)
            assert (sum(parts) % self.mod) == secret
            result = []
            for sub, child in zip(parts, f.children):
                result.extend(self.split(sub, child))
            return result


class Restorer(MathBase):
    def __init__(self, conf: Configuration, vals: dict[Any, int]):
        super().__init__(conf)
        self.vals = vals

    def _restore_threshold(self, f: BooleanNode) -> int | None:
        if f.kind != NodeKind.THRESHOLD:
            return self.restore(f)
        xs = []
        ys = []
        for n, child in enumerate(f.children, 1):
            s = self.restore(child)
            if s is not None:
                xs.append(n)
                ys.append(s)
        
        if len(xs) < f.threshold:
            return None

        secret = 0
        x0 = 0
        for j in range(f.threshold):
            product = 1
            for i in range(f.threshold):
                if i != j:
                    a = x0 - xs[i]
                    b = xs[j] - xs[i]
                    product *= a * self.inv(b)
                    product %= self.mod
            secret += ys[j] * product
            secret %= self.mod
        return secret

    def restore(self, f: BooleanNode) -> int | None:
        if f.kind == NodeKind.VAR:
            if f.name not in self.vals:
                return None
            return self.vals[f.name]
        if f.kind == NodeKind.THRESHOLD:
            return self._restore_threshold(f)
        if f.kind == NodeKind.OR:
            for child in f.children:
                if restored := self.restore(child):
                    return restored
            return None
        if f.kind == NodeKind.AND:
            result = 0
            for child in f.children:
                restored = self.restore(child)
                if restored is None:
                    return None
                result += restored
                result %= self.mod
            return result
