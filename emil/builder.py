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

            #  next がある場合（「った」等）は、それが次の input に繋がる場合のみ通す
            if not e.next:
                n = EntryNode(entry=e, child=None)
                current.append(n)
            elif tail_input.startswith(e.next):
                if not tail.entry.is_direct_inputtable or rule.allow_direct_next_input:
                    # 次の Entry が直接入力の場合は、設定により next を使って遷移していいかどうか決める
                    n = EntryNode(entry=e, child=tail)
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
    # "こっち" のノード列形成例
    #   こ          っ            ち
    #  [ko, co] -> [ltu, xtu] -> [ti, chi]
    #           -> [tt]       -> [ti] ※ tt からは ti にしか遷移できない
    #           -> [cc]       -> [chi] ※ cc からは chi にしか遷移できない
    parents = search_parents(rule, text, tail)
    for p in parents:
        current_inputtable = inputtables.setdefault(len(text)-len(p.entry.output), set())
        if p in current_inputtable:
            return
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


def main():
    from pprint import pprint
    p = data.filepath("google_ime_default_roman_table.txt")
    # p = data.filepath("google_ime_default_roman_table.txt")
    p = data.filepath("test_data.txt")
    rule = Rule.from_file(p, {chr(i) for i in range(128) if chr(i).isprintable()})
    rule.allow_direct_next_input = True
    # text = "こんkっち"
    # text = "っっt"
    text = "さ"
    # text = "んう"
    # text = "あい"
    at = build_automaton(rule, text)

    def pnode(n: Node, indent: int):
        print(indent * " " + f"Node: {id(n) % 1000}")
        for e in n.next_edges:
            print(indent * " " + "  Edge: " +
                  " | ".join(f"{entry.input}/{entry.output}/{entry.next}" for entry in e.entries))
            pnode(e.next, indent + 2)

    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    # pnode(at.initial_node, 0)

    from .viz import render
    r = render(at)
    with open("dot.txt", mode="w", encoding="utf-8") as fp:
        fp.write(r)

    # for e, ei, ii in at._state.available_edges:
    #     print(e.entries[0].input)
    # for c in "XA":
    for c in "XA":
        print("input:", c)
        pprint(at.input(c))
        print("inputted:", at.inputted, "outputted:", at.outputted)
    print("passed_entries:")
    pprint(at._state.passed_entries)
    #     pprint(at.input(c))
    #     print("inputted:", at.inputted, "outputted:", at.outputted)
    # print("passed_entries:")
    # pprint(at._state.passed_entries)


if __name__ == '__main__':
    main()
