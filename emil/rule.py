# coding: utf-8
from __future__ import annotations
from typing import Optional, List, Dict, Set
import dataclasses
from dataclasses import dataclass
from . import data
from .strings import split_prefixes


@dataclass
class Entry:
    input: str
    output: str
    next: str
    # 以下は post_init で初期化
    # この Entry を入力する前に入力が必要な Entry のリスト
    #dependencies: List[Entry] = dataclasses.field(init=False, default_factory=list)
    # この Entry の input が他の Entry の common prefix かどうか
    #has_only_common_prefix: bool = False

    def __hash__(self):
        return hash((self.input, self.output, self.next))


@dataclass
class DependentEntry(Entry):
    # この Entry を入力する前に入力が必要な Entry のリスト
    dependencies: List[DependentEntry] = dataclasses.field(init=False, default_factory=list)
    # この Entry を入力する前に入力しても良い Entry のリスト
    substitutables: List[DependentEntry] = dataclasses.field(init=False, default_factory=list)
    # この Entry の input が他の Entry の common prefix かどうか
    has_only_common_prefix: bool = False
    # 直接入力可能な Entry かどうか
    is_direct_inputtable: bool = False

    def __hash__(self):
        return hash((self.input, self.output, self.next))


@dataclass
class Rule:
    elist: List[Entry]
    direct_inputtable: Set[str]
    # 次の入力を使って、直接入力可能な Entry を入力済みにしたことにできるかどうか
    allow_direct_next_input: bool = False

    # 以下は post_init で初期化
    dependent_entry_list: List[DependentEntry] = dataclasses.field(init=False)
    input_edict: Dict[str, DependentEntry] = dataclasses.field(init=False)
    output_edict: Dict[str, List[DependentEntry]] = dataclasses.field(init=False)
    max_output_length: int = 0
    __only_next_edict: Dict[str, List[DependentEntry]] = dataclasses.field(init=False)

    def __post_init__(self):
        self.max_output_length = max(len(e.output) for e in self.elist)
        self.make_dict()
        self.fill_dependencies()
        self.fill_substitutables()
        self.fill_common_prefix()

    def fill_substitutables(self):
        next_edict = self.__only_next_edict

        def fill(e: DependentEntry):
            for i in range(len(e.input)):
                substr = e.input[:i+1]
                if substr in next_edict:
                    e.substitutables.extend(next_edict[substr])

        for e in self.dependent_entry_list:
            if not e.dependencies:
                fill(e)

    def fill_dependencies(self):
        direct = self.direct_inputtable
        next_edict = self.__only_next_edict

        def fill(e: DependentEntry):
            for i, c in enumerate(reversed(e.input)):
                if c not in direct:
                    # 直接入力ができない文字が input に含まれている場合は、事前に入力すべき依存関係として
                    # その文字を「次の入力」に含む entry を探す
                    next_required_substr = e.input[:len(e.input)-i]
                    if next_required_substr in next_edict:
                        # ここで fill するのは、ある entry を入力する前に必ず入力すべき entry なので
                        # output がある entry は無視する
                        e.dependencies.extend(next_edict[next_required_substr])
                        return
                    raise Exception(f"cannot input entry: {e}")

        for e in self.dependent_entry_list:
            fill(e)

    def fill_common_prefix(self):
        input_edict = self.input_edict
        for e in self.elist:
            prefixes = split_prefixes(e.input, len(e.input)-1)
            for p in prefixes:
                if p in input_edict:
                    input_edict[p].has_only_common_prefix = True

    def make_dict(self):
        i = self.input_edict = {}
        o = self.output_edict = {}
        n = self.__only_next_edict = {}
        d = self.dependent_entry_list = []
        for e in self.elist:
            if not e.input:
                raise Exception(f"input is required: {e}")
            if not e.output and not e.next:
                raise Exception(f"either either output or next is required: {e}")
            if e.input in i and i[e.input].output == e.output:
                raise Exception(f"duplicate entry: {e}")
            de = DependentEntry(input=e.input, output=e.output, next=e.next)
            i[e.input] = de
            d.append(de)
            if de.output:
                o.setdefault(de.output, []).append(de)
            if not de.output and de.next:
                n.setdefault(de.next, []).append(de)

    @staticmethod
    def from_file(entry_file_path: str, direct_inputtable: Set[str]) -> Rule:
        elist = []
        with open(entry_file_path, encoding="utf-8") as f:
            for line in f:
                cols = line.strip("\n").split("\t")
                if len(cols) == 3:
                    pass
                elif len(cols) == 2:
                    cols = [*cols, ""]
                else:
                    raise Exception(f"invalid entry: {line}")
                e = Entry(input=cols[0], output=cols[1], next=cols[2])
                if not e.input:
                    raise Exception(f"invalid input: {e}")
                elist.append(e)
        return Rule(elist, direct_inputtable=direct_inputtable)
