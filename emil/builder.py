# coding: utf-8
from __future__ import annotations
from typing import Optional, List, Dict, Set
import dataclasses
from dataclasses import dataclass
from . import data
from .rule import Rule, DependentEntry, Entry
from .automaton import Automaton, Node, Edge
from .strings import split_prefixes, split_suffixes


@dataclass(frozen=True)
class EntryNode:
    entry: DependentEntry
    child: Optional[EntryNode]

    def total_length(self) -> int:
        entry_len = len(self.entry.output)
        if not self.child:
            return entry_len
        return entry_len + self.child.total_length()

    def children(self) -> List[DependentEntry]:
        """ 自身を含む """
        s = [self.entry]
        if not self.child:
            return s
        return s + self.child.children()

    def flatten_dependencies(self) -> List[List[DependentEntry]]:
        """ 自身は含まない """
        def backtrack(entry, current_stack, result):
            if not entry.dependencies or entry.substitutables:
                result.append(current_stack)
            for d in entry.dependencies:
                new_stack = current_stack[:]
                new_stack.insert(0, d)
                backtrack(d, new_stack, result)
            for s in entry.substitutables:
                new_stack = current_stack[:]
                new_stack.insert(0, s)
                backtrack(s, new_stack, result)
        result: List[List[DependentEntry]] = []
        backtrack(self.entry, [], result)
        return result

    def __hash__(self):
        return hash(self.entry)


def search_parents(rule: Rule, text: str, tail: EntryNode) -> List[EntryNode]:
    if not text:
        return []
    current = []
    tail_input = tail.entry.input if tail.entry else ""
    tail_input_prefixes = split_prefixes(tail_input, len(tail_input))
    text_suffixes = split_suffixes(text, rule.max_output_length)

    for s in text_suffixes:
        for e in rule.output_edict.get(s, []):
            #  next がある場合（「った」等）は、それが次の input に繋がる場合のみ通す
            if e.next:
                if tail_input.startswith(e.next):
                    if not tail.entry.is_direct_inputtable:
                        # 次の Entry が直接入力の場合は、設定により next を使って遷移していいかどうか決める
                        n = EntryNode(entry=e, child=tail)
                        current.append(n)
                continue

            if e.has_only_common_prefix:
                # 単独では確定できない common prefix のみの Entry は末尾の入力には使えない
                # ※configuarable にするのもあり
                if not tail_input:
                    continue

                # 「今回の input + 次に来る input prefix（のいずれか）」を input に持つ
                # Entry の場合は「んい」「んに」を正しく入力できないので無視する
                # 「んk」のようにかな＋直接入力可能な文字列にもここで対応する
                if any(1 for p in tail_input_prefixes if (e.input + p) in rule.input_edict):
                    continue

                n = EntryNode(entry=e, child=tail)
                current.append(n)
                continue

            n = EntryNode(entry=e, child=None)
            current.append(n)

        for e in rule.output_with_next_edict.get(s, []):
            # next を output として扱ったときに入力候補にできるかチェックする
            #
            # 出題: "っt"
            # entry: tt/っ/t
            # tt で打てるようにするかどうか
            # 出題: "かち"
            # entry: k//か
            # entry: t//ち
            # entry: hh/か/ち
            # kt OR hh で打てるようにする
            # TODO: いずれの Entry からも依存されてない場合のみ使える、とかにしたほうが良いかも
            # j		か
            # かg		かが
            # z	が
            d = dataclasses.replace(e, next="", output=e.output + e.next)
            d.dependencies = e.dependencies
            d.substitutables = e.substitutables
            d.has_only_common_prefix = e.has_only_common_prefix
            d.is_direct_inputtable = e.is_direct_inputtable
            n = EntryNode(entry=d, child=None)
            current.append(n)

        # 直接入力可能かどうか
        if s in rule.direct_inputtable:
            e = DependentEntry(input=s, output=s, next="", is_direct_inputtable=True)
            n = EntryNode(entry=e, child=None)
            current.append(n)

    if not current:
        raise Exception(f"any of {text_suffixes} is NOT matched to rules")

    return current


def build_index_based_inputtable(rule: Rule, text: str, tail: EntryNode, inputtables: Dict[int, Set[EntryNode]]):
    """表示文字列の入力済み文字数に対応する、そのとき遷移可能な Entry のリストを返す"""
    if not text:
        return

    parents = search_parents(rule, text, tail)
    for p in parents:
        current_inputtable = inputtables.setdefault(len(text)-len(p.entry.output), set())
        if p in current_inputtable:
            continue
        current_inputtable.add(p)
        next_text = text[:len(text)-len(p.entry.output)]
        build_index_based_inputtable(rule, next_text, p, inputtables)
    return inputtables


def build_automaton(rule: Rule, text: str):
    en_tail = EntryNode(entry=DependentEntry("", "", ""), child=None)
    indexes: Dict[int, Set[EntryNode]] = build_index_based_inputtable(rule, text, en_tail, {})
    indexed_nodes: Dict[int, Node] = {}

    def build_nodes(previous_node: Node, end_node: Node, index: int):
        if previous_node is end_node:
            return

        for n in indexes[index]:
            build = False
            next_index = index + n.total_length()
            if next_index == len(text):
                next_node = end_node
            elif next_index in indexed_nodes:
                next_node = indexed_nodes[next_index]
            else:
                next_node = indexed_nodes[next_index] = Node()
                build = True
            children = n.children()
            deps = n.flatten_dependencies()
            for d in deps:
                entries = [Entry(e.input, e.output, e.next) for e in d+children]
                edge = Edge(entries=entries, previous=previous_node, next=next_node)
                previous_node.next_edges.append(edge)
            if build:
                build_nodes(next_node, end_node, next_index)

    start = Node()
    end = Node()
    build_nodes(start, end, 0)
    return Automaton(start, end)
