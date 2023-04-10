from collections import Counter
from dataclasses import dataclass
from typing import Any, TypeVar
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode

from .parse import parse
from .boolean import BooleanNode, NodeKind
import secrets
import random

T = TypeVar("T")


@dataclass
class Part:
    name: str
    values: list[int]

    def serialize(self) -> str:
        data = {"name": self.name, "values": self.values}
        return urlsafe_b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    @classmethod
    def deserialize(cls, s: str) -> "Part":
        data = json.loads(urlsafe_b64decode(s).decode("utf-8"))
        return cls(name=data["name"], values=data["values"])


@dataclass(kw_only=True)
class Configuration:
    modulo: int
    formula: str
    version: int = 1

    def serialize(self) -> str:
        data = {"modulo": self.modulo, "formula": self.formula, "version": self.version}
        return urlsafe_b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    @classmethod
    def deserialize(cls, s: str) -> "Part":
        data = json.loads(urlsafe_b64decode(s).decode("utf-8"))
        return cls(modulo=data["modulo"], formula=data["formula"], version=data["version"])

    def make_formula(self) -> BooleanNode:
        formula: BooleanNode = parse(self.formula)
        counter = Counter()

        def walker(node: BooleanNode):
            if node.kind == NodeKind.VAR:
                counter[node.name] = counter[node.name] + 1
                node = BooleanNode.var((node.name, counter[node.name]))
            return node

        return formula.walk(walker)
    
    def names(self) -> set[str]:
        result = set()
        def walker(node: BooleanNode):
            if node.kind == NodeKind.VAR:
                result.add(node.name)
        parse(self.formula).walk(walker)
        return result

    def split(self, secret: int, seed=None, assigned=None) -> list[Part]:
        formula = self.make_formula()
        secret %= self.modulo
        splitter = Splitter(self, seed=seed, assigned=assigned)
        splitter.split(secret, formula)
        split = list(splitter.assigned.items())
        split.sort(key=lambda x: x[0][1])
        result = {}
        for key, val in split:
            name, idx = key
            if name not in result:
                result[name] = Part(name, [])
            assert idx - 1 == len(result[name].values)
            result[name].values.append(val)
        return list(result.values())

    def restore(self, parts: list[Part]) -> int | None:
        formula = self.make_formula()
        given = {}
        for part in parts:
            for idx, val in enumerate(part.values, 1):
                given[(part.name, idx)] = val
        return Restorer(self, given).restore(formula)

    def modify(self, new: "Configuration", parts: list[Part], seed: int = None):
        secret = self.restore(parts)
        if not secret:
            raise ValueError("unable to restore secret")
        assigned = {}
        for part in parts:
            for idx, val in enumerate(part.values, 1):
                assigned[(part.name, idx)] = val
        def visitor(f: BooleanNode):
            if f.kind == NodeKind.VAR:
                if f.name not in assigned:
                    assigned[f.name] = None
        self.make_formula().walk(visitor)
        print(assigned)
        return new.split(secret, seed=seed, assigned=assigned)


class MathBase:
    def __init__(self, conf: Configuration, seed=None) -> None:
        self.conf = conf
        self._rng = random.Random(seed) if seed is not None else None

    @property
    def mod(self) -> int:
        return self.conf.modulo

    def rand(self, n=None) -> int | list[int]:
        if n is None:
            if self._rng:
                return self._rng.randint(0, self.mod - 1)
            else:
                return secrets.randbelow(self.mod)
        return [self.rand() for _ in range(n)]

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
    def __init__(self, conf: Configuration, assigned: dict[Any, int] = None, **kwargs) -> None:
        super().__init__(conf, **kwargs)
        self.assigned = assigned or {}

    def _assign(self, key: Any, val: int, is_random: bool):
        if is_random and key in self.assigned:
            if self.assigned[key] is None:
                raise ValueError(f"can't assign random value to {key}, but required to")
            else:
                print(f'changing value for {val}')
        self.assigned[key] = val

    def _try_restore_poly(self, f: BooleanNode) -> list[int] | None:
        restorer = Restorer(self.conf, self.assigned)
        evaluated = []
        for i in range(len(f.children) + 1):
            val = restorer._restore_threshold(f, at=i)
            if val is None:
                return None
            evaluated.append(val)
        return evaluated

    def _try_restore(self, f: BooleanNode) -> list[int] | None:
        return Restorer(self.conf, self.assigned).restore(f)

    def _split_threshold(self, secret: int, f: BooleanNode, is_random: bool):
        if f.kind != NodeKind.THRESHOLD:
            return self.split(secret, f)

        k = f.threshold
        evaluated = self._try_restore_poly(f)
        if evaluated and evaluated[0] != secret:
            raise Exception("wrong polynom restored")
        if not evaluated:
            # Generate new poly then
            poly = [secret] + self.rand(k - 1)
            is_random = True

            def evaluate(x):
                res = 0
                xpow = 1
                for i in poly:
                    res += i * xpow
                    res %= self.mod
                    xpow *= x
                    xpow %= self.mod
                return res

            evaluated = [evaluate(i) for i in range(len(f.children) + 1)]

        assert evaluated[0] == secret
        for n, child in enumerate(f.children, 1):
            subsecret = evaluated[n]
            self.split(subsecret, child, is_random=is_random)

    def _split_and(self, secret: int, f: BooleanNode, is_random: bool):
        free = []
        summ = 0

        for child in f.children:
            subsecret = self._try_restore(child)
            if not subsecret:
                free.append(child)
                continue
            print(f'{child} = {subsecret}')
            summ += subsecret
            summ %= self.mod
            self.split(subsecret, child, is_random=is_random)

        if not free:
            if summ != secret:
                raise Exception(f"invalid secret restored: {summ}")
            return

        for child in free[:-1]:
            subsecret = self.rand()
            summ += subsecret
            summ %= self.mod
            self.split(subsecret, child, is_random=True)

        child = free[-1]
        subsecret = (secret - summ) % self.mod
        summ += subsecret
        summ %= self.mod
        self.split(subsecret, child, is_random=len(free) > 1)

        assert summ == secret

    def split(self, secret: int, f: BooleanNode, is_random: bool = False) -> list[tuple[Any, int]]:
        if f.kind == NodeKind.VAR:
            self._assign(f.name, secret, is_random=is_random)
        if f.kind == NodeKind.THRESHOLD:
            self._split_threshold(secret, f, is_random=is_random)
        if f.kind == NodeKind.OR:
            result = []
            for child in f.children:
                self.split(secret, child, is_random=is_random)
            return result
        if f.kind == NodeKind.AND:
            self._split_and(secret, f, is_random=is_random)


class Restorer(MathBase):
    def __init__(self, conf: Configuration, given: dict[Any, int]):
        super().__init__(conf)
        self.given = given

    def _restore_threshold(self, f: BooleanNode, at=0) -> int | None:
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
        x0 = at
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
            if f.name not in self.given:
                return None
            return self.given[f.name]
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
