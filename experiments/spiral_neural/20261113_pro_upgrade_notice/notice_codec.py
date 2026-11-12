"""UR1: an isolated, fixed-root upgrade-notice codec, not a neural model.

The caller explicitly selects the UR1 notice entry/profile. Ordinary data is
never searched for control words. The root header and address coding stay at
c=3; this module does not implement root growth or legacy-profile migration.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Sequence


PROFILE_ID = "SLE-UR1-fixed-root-c3"
ROOT_N = 3
ROOT_K = 2
ROOT_MARKER = "001"
REPETITIONS = 3
MAX_DEPTH = (1 << ROOT_N) - 1
MAX_CHILD_ID = (1 << ROOT_N) - 1
CONTROL_ROLES = frozenset(("control", "operator"))
ROLES = CONTROL_ROLES | {"data", "address"}


class NoticeError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _positive(name: str, value: int) -> None:
    if type(value) is not int or value < 1:
        raise NoticeError("INVALID_ARGUMENT", f"{name} must be a positive integer")


def _binary(bits: str) -> None:
    if not isinstance(bits, str) or any(bit not in "01" for bit in bits):
        raise NoticeError("NON_BINARY", "only raw 0/1 bits are accepted")


def _profile(profile_id: str) -> None:
    if profile_id != PROFILE_ID:
        raise NoticeError("UNKNOWN_PROFILE", "the explicit UR1 notice profile is required")


def word(value: int, n: int, k: int = 1) -> str:
    """Encode a numeric field. No control-role reservation applies here."""
    _positive("n", n)
    _positive("k", k)
    if type(value) is not int or not 0 <= value < (1 << n):
        raise NoticeError("VALUE_RANGE", "value does not fit the information width")
    return format(value, f"0{n}b") + "0" * k


def up(n: int, k: int) -> str:
    _positive("n", n)
    _positive("k", k)
    return "1" * n + "0" * k


def end(n: int, k: int) -> str:
    _positive("n", n)
    _positive("k", k)
    return "1" * (n - 1) + "0" * (k + 1)


ROOT_HEADER = ROOT_MARKER + up(ROOT_N, ROOT_K)


def ordinary_capacity(n: int, role: str) -> int:
    _positive("n", n)
    if role not in ROLES:
        raise NoticeError("UNKNOWN_ROLE", role)
    return (1 << n) - (2 if role in CONTROL_ROLES else 0)


@dataclass(frozen=True)
class Branch:
    name: str
    role: str
    n: int
    k: int
    ordinary_ids: tuple[int, ...] = ()
    # An explicit branch-local mark, including any deleted ordinary IDs.
    highwater: int = -1

    def __post_init__(self) -> None:
        _positive("k", self.k)
        capacity = ordinary_capacity(self.n, self.role)
        if (type(self.highwater) is not int or self.highwater < -1
                or self.highwater >= capacity):
            raise NoticeError("INVALID_BRANCH", "highwater does not fit this role")
        if any(type(value) is not int or not 0 <= value <= self.highwater
               for value in self.ordinary_ids):
            raise NoticeError("INVALID_BRANCH", "ordinary IDs must fit the branch highwater")
        if len(set(self.ordinary_ids)) != len(self.ordinary_ids):
            raise NoticeError("INVALID_BRANCH", "ordinary IDs must be unique")


@dataclass(frozen=True)
class Node:
    branch: Branch | None = None
    children: dict[int, Node] = field(default_factory=dict)


def ordinary_word(value: int, branch: Branch) -> str:
    bits = word(value, branch.n, branch.k)
    if value >= ordinary_capacity(branch.n, branch.role):
        raise NoticeError("RESERVED_CONTROL", "UP and END are not ordinary control/operator IDs")
    return bits


def _read_word(bits: str, pos: int, n: int, k: int) -> tuple[int, int]:
    stop = pos + n + k
    if stop > len(bits):
        raise NoticeError("TRUNCATED", "incomplete word")
    if bits[pos + n:stop] != "0" * k:
        raise NoticeError("BAD_SUFFIX", "suffix differs from the known k")
    return int(bits[pos:pos + n], 2), stop


def ordinary_value(bits: str, branch: Branch) -> int:
    _binary(bits)
    value, stop = _read_word(bits, 0, branch.n, branch.k)
    if stop != len(bits):
        raise NoticeError("EXTRA_BITS", "expected one ordinary word")
    if value >= ordinary_capacity(branch.n, branch.role):
        raise NoticeError("RESERVED_CONTROL", "control-role reservation")
    return value


def _address(address: Sequence[int]) -> tuple[int, ...]:
    path = tuple(address)
    if not path:
        raise NoticeError("ROOT_GROWTH_UNSUPPORTED", "UR1 does not notify the root itself")
    if len(path) > MAX_DEPTH:
        raise NoticeError("ADDRESS_CAPACITY", "fixed c=3 permits at most seven child IDs")
    if any(type(child) is not int or not 0 <= child <= MAX_CHILD_ID for child in path):
        raise NoticeError("ADDRESS_CAPACITY", "each stable child ID must be in 0..7")
    return path


def encode_address(address: Sequence[int]) -> str:
    path = _address(address)
    return word(len(path), ROOT_N, 1) + "".join(word(child, ROOT_N, 1) for child in path)


def _read_address(bits: str, pos: int) -> tuple[tuple[int, ...], str, int]:
    start = pos
    count, pos = _read_word(bits, pos, ROOT_N, 1)
    if count == 0:
        raise NoticeError("ROOT_GROWTH_UNSUPPORTED", "an empty address is unsupported")
    path = []
    for _ in range(count):
        child, pos = _read_word(bits, pos, ROOT_N, 1)
        path.append(child)
    return tuple(path), bits[start:pos], pos


def decode_address(bits: str) -> tuple[int, ...]:
    _binary(bits)
    path, _, stop = _read_address(bits, 0)
    if stop != len(bits):
        raise NoticeError("EXTRA_BITS", "address has trailing bits")
    return path


def branch_at(tree: Node, address: Sequence[int]) -> Branch:
    path = _address(address)
    node = tree
    for child in path:
        if child not in node.children:
            raise NoticeError("UNKNOWN_ADDRESS", f"no target at {path}")
        node = node.children[child]
    if node.branch is None:
        raise NoticeError("UNSUPPORTED_INTERNAL_NODE", "this node has no notifiable branch profile")
    return node.branch


def _target_n(bits: str, pos: int) -> int:
    # Only the explicitly selected notice's UP slot has this restricted form.
    start = pos
    while pos < len(bits) and bits[pos] == "1":
        pos += 1
    if pos == len(bits):
        raise NoticeError("TRUNCATED", "target UP has no complete suffix")
    if pos == start:
        raise NoticeError("BAD_UP", "target UP must begin with information ones")
    return pos - start


def _expect(bits: str, pos: int, expected: str, code: str) -> int:
    stop = pos + len(expected)
    if stop > len(bits):
        raise NoticeError("TRUNCATED", "incomplete notice field")
    if bits[pos:stop] != expected:
        raise NoticeError(code, "notice field differs from its required exact word")
    return stop


def _transition(current: int, target: int) -> None:
    if target < current:
        raise NoticeError("STALE_TARGET", "a notice cannot shrink a branch")
    if target > current + 1:
        raise NoticeError("JUMP_TARGET", "one notice can grow only one information bit")


@dataclass(frozen=True)
class Notice:
    address: tuple[int, ...]
    address_bits: str
    current_n: int
    target_n: int
    k: int
    up_bits: str
    end_bits: str


def encode_notice(address: Sequence[int], target_n: int, tree: Node) -> str:
    """Build a syntactic UR1 frame; the receiver checks current/target ordering."""
    branch = branch_at(tree, address)
    token = up(target_n, branch.k)
    return ROOT_HEADER + encode_address(address) + token * REPETITIONS + end(target_n, branch.k)


def decode_notice(bits: str, tree: Node, *, profile_id: str) -> Notice:
    """Pure validation: no tree changes and no implicit ordinary-data dispatch."""
    _profile(profile_id)
    _binary(bits)
    pos = _expect(bits, 0, ROOT_HEADER, "BAD_ROOT_HEADER")
    path, address_bits, pos = _read_address(bits, pos)
    branch = branch_at(tree, path)
    target = _target_n(bits, pos)
    token, terminator = up(target, branch.k), end(target, branch.k)
    for _ in range(REPETITIONS):
        pos = _expect(bits, pos, token, "MIXED_UP")
    pos = _expect(bits, pos, terminator, "BAD_END")
    if pos != len(bits):
        raise NoticeError("EXTRA_BITS", "notice contains trailing bits")
    _transition(branch.n, target)
    return Notice(path, address_bits, branch.n, target, branch.k, token, terminator)


def encode_reply(notice: Notice) -> str:
    """Only the exact count/path bits plus one target UP; STOP is external."""
    return notice.address_bits + notice.up_bits


def decode_reply(bits: str, tree: Node, *, profile_id: str) -> Notice:
    """Parse a reply; use verify_reply to match an outstanding request."""
    _profile(profile_id)
    _binary(bits)
    path, address_bits, pos = _read_address(bits, 0)
    branch = branch_at(tree, path)
    target = _target_n(bits, pos)
    token = up(target, branch.k)
    pos = _expect(bits, pos, token, "BAD_UP")
    if pos != len(bits):
        raise NoticeError("EXTRA_BITS", "reply must contain exactly one target UP and no END")
    _transition(branch.n, target)
    return Notice(path, address_bits, branch.n, target, branch.k, token, end(target, branch.k))


def verify_reply(expected_notice: Notice, bits: str, tree: Node, *, profile_id: str) -> Notice:
    """Require the exact address/count and target UP for this request."""
    reply = decode_reply(bits, tree, profile_id=profile_id)
    if bits != encode_reply(expected_notice):
        raise NoticeError("REPLY_MISMATCH", "valid reply does not confirm the outstanding notice")
    return reply


def _replace_branch(tree: Node, path: tuple[int, ...], branch: Branch) -> Node:
    if not path:
        return replace(tree, branch=branch)
    children = dict(tree.children)
    children[path[0]] = _replace_branch(children[path[0]], path[1:], branch)
    return replace(tree, children=children)


def _require_tree(tree: Node) -> None:
    """A width-bearing node has one canonical path; DAGs and cycles are unsupported."""
    seen: set[int] = set()
    pending = [tree]
    while pending:
        node = pending.pop()
        if not isinstance(node, Node):
            raise NoticeError("INVALID_TREE", "every child must be a Node")
        if id(node) in seen:
            raise NoticeError("NOT_A_TREE", "a shared Node identity or cycle has no unique canonical path")
        seen.add(id(node))
        pending.extend(node.children.values())


@dataclass(frozen=True)
class Receipt:
    status: str
    reply_bits: str
    external_stop: bool
    address: tuple[int, ...]
    target_n: int


class NoticeReceiver:
    """Single-process, in-memory receiver; validation precedes a state commit."""

    def __init__(self, tree: Node | None = None):
        source = fixture_tree() if tree is None else tree
        _require_tree(source)
        self.tree = deepcopy(source)
        self.applied_transitions = 0

    def receive_notice(self, bits: str, *, profile_id: str) -> Receipt:
        notice = decode_notice(bits, self.tree, profile_id=profile_id)
        changed = notice.target_n == notice.current_n + 1
        receipt = Receipt("upgraded" if changed else "already_current", encode_reply(notice),
                          True, notice.address, notice.target_n)
        if changed:
            branch = branch_at(self.tree, notice.address)
            candidate = _replace_branch(self.tree, notice.address, replace(branch, n=notice.target_n))
            # No mutation occurs while the three UPs, END, and exact length are checked.
            self.tree = candidate
            self.applied_transitions += 1
        return receipt


FIXTURE_PATHS = ((0,), (1,), (2,), (3,), (4,), (5, 0), (5, 1), (5, 5, 0))


def fixture_tree() -> Node:
    """Synthetic stable child IDs, not a replacement for any historical tree."""
    def operator(name: str) -> Node:
        # ID 3 was allocated then deleted: it still belongs in the highwater.
        return Node(Branch(name, "operator", 4, 1, (0, 1, 2), 3))

    return Node(children={
        0: operator("operator"),
        1: Node(Branch("dataA", "data", 4, 1)),
        2: Node(Branch("dataB", "data", 4, 1)),
        3: Node(Branch("category", "control", 3, 2, (0, 1), 2)),
        4: Node(Branch("version", "control", 3, 3, (0,), 1)),
        5: Node(children={
            0: operator("geometry.operator"),
            1: Node(Branch("geometry.dataA", "data", 4, 1)),
            5: Node(children={0: operator("nested.operator")}),
        }),
    })
