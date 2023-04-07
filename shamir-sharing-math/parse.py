from dataclasses import dataclass
from typing import Any, Callable

from .boolean import BooleanNode

__all__ = ("parse",)

"""
WHITESPACE = _{ " " }
number = { ('0'..'9')+ }
name = { ('a'..'z')+ }

threshold = {
	"T" ~ number ~ "("
    ~ (expression ~ ("," ~ expression)*)?
    ~ ")"
}

brackets = { "(" ~ expression ~ ")" }

term = { brackets | threshold | name }
and = { term ~ ("&" ~ term)* }
or = { and ~ ("|" ~ and)* }

expression = { or }
main = { SOI ~ expression ~ EOI }
"""


@dataclass(frozen=True)
class Slice:
    data: str
    start: int = 0

    def get(self) -> str:
        return self.data[self.start :]

    def consume(self, f) -> tuple[str, "Slice"]:
        curr = self.start
        while curr < len(self.data) and f(self.data[curr]):
            curr += 1
        consumed = self.data[self.start : curr]
        return consumed, Slice(self.data, curr)


class ParseError(ValueError):
    def __init__(self, name: str, slice: Slice) -> None:
        self.name = name

        context_size = 35
        begin = max(0, slice.start - context_size)
        end = min(len(slice.data), slice.start + context_size)
        context = slice.data[begin:end]
        pointer = "_" * (slice.start - begin) + "^" + "_" * max(0, end - slice.start - 2)
        msg = f"Expected {name}\n> {context}\n> {pointer}"
        super().__init__(msg)


Parser = Callable[[Slice], tuple[Any, Slice]]


def parse_all(*parsers: list[Parser]) -> Parser:
    def parse_all(s: Slice) -> tuple[list, Slice]:
        result = []
        for p in parsers:
            res, s = p(s)
            result.append(res)
        return result, s

    return parse_all


def parse_any(*parsers) -> Parser:
    def parse_any(s: Slice) -> tuple[list, Slice]:
        names = []
        for p in parsers:
            try:
                return p(s)
            except ParseError as e:
                names.append(e)
        raise ParseError(" or ".join(names), s)

    return parse_any


def skip_ws(s: Slice) -> tuple[str, Slice]:
    return s.consume(str.isspace)


def parse_eof(s: Slice) -> tuple[None, Slice]:
    _, s = skip_ws(s)
    if s.start < len(s.data):
        raise ParseError("EOF", s)
    return None, s


def parse_literal(needle: str) -> Parser:
    def parse_literal(s: Slice) -> tuple[str, "Slice"]:
        _, s = skip_ws(s)
        end = s.start + len(needle)
        if s.data[s.start : end] == needle:
            return needle, Slice(s.data, end)
        raise ParseError(f"`{needle}`", s)

    return parse_literal


def parse_number(s: Slice) -> tuple[int, Slice]:
    _, s = skip_ws(s)
    num, rest = s.consume(str.isdigit)
    if not num:
        raise ParseError("number", s)
    return int(num), rest


def parse_name(s: Slice) -> tuple[str, Slice]:
    _, s = skip_ws(s)
    name, rest = s.consume(lambda ch: ch not in (",", "|", "&", ")", "("))

    for spaces in range(len(name)):
        ch = name[-spaces - 1]
        if not ch.isspace():
            break
    if spaces:
        name = name[:-spaces]
        rest = Slice(rest.data, rest.start - spaces)

    if not name:
        raise ParseError("name", s)
    return name, rest


def parse_splitted(separator: Parser, parser: Parser) -> Parser:
    def parse_splitted(s: Slice) -> tuple[list, Slice]:
        first, s = parser(s)
        result = [first]
        while True:
            try:
                _, new_s = separator(s)
                child, new_s = parser(new_s)
                result.append(child)
                s = new_s
            except ParseError as e:
                break
        return result, s

    return parse_splitted


def parse_threshold(s: Slice) -> tuple[BooleanNode, Slice]:
    _, s = parse_literal("T")(s)
    num, s = parse_number(s)
    _, s = parse_literal("(")(s)
    children, s = parse_splitted(parse_literal(","), parse_expression)(s)
    _, s = parse_literal(")")(s)
    node = BooleanNode.thresh(num, *children)
    return node, s


def parse_brackets(s: Slice) -> tuple[BooleanNode, Slice]:
    _, s = parse_literal("(")(s)
    inner, s = parse_expression(s)
    _, s = parse_literal(")")(s)
    return inner, s


def parse_var(s: Slice) -> tuple[BooleanNode, Slice]:
    name, s = parse_name(s)
    return BooleanNode.var(name), s


def parse_term(s: Slice) -> tuple[BooleanNode, Slice]:
    try:
        peek = s
        _, peek = parse_literal("(")(peek)
    except ParseError:
        pass
    else:
        return parse_brackets(s)

    try:
        peek = s
        _, peek = parse_literal("T")(peek)
        num, peek = parse_number(peek)
        _, peek = parse_literal("(")(peek)
    except ParseError:
        pass
    else:
        return parse_threshold(s)

    return parse_var(s)


def parse_and(s: Slice) -> tuple[BooleanNode, Slice]:
    children, s = parse_splitted(parse_literal("&"), parse_term)(s)
    node = BooleanNode.and_(*children)
    return node, s


def parse_or(s: Slice) -> tuple[BooleanNode, Slice]:
    children, s = parse_splitted(parse_literal("|"), parse_and)(s)
    node = BooleanNode.or_(*children)
    return node, s


parse_expression = parse_or


def parse(s: str) -> BooleanNode:
    res, rest = parse_expression(Slice(s))
    parse_eof(rest)
    return res
