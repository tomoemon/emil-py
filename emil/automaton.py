# coding: utf-8
from __future__ import annotations
from typing import Optional, List, Dict, Set, Tuple
import dataclasses
from dataclasses import dataclass
from .rule import Entry


# 表示文字列の入力状態を表す
@dataclass
class Node:
    next_edges: List[Edge] = dataclasses.field(init=False, default_factory=list)

    @property
    def finished(self) -> bool:
        return bool(self.next_edges)


# 次の Node へ遷移するための入力
@dataclass
class Edge:
    entries: List[Entry]
    previous: Node
    next: Node


@dataclass
class InputResult:
    succeeded: bool
    new_state: State
    # 次の入力による自動遷移が行われる場合、1入力に対して複数の Entry が入力完了になる場合がある
    passed_entries: Tuple[Entry, ...]


@dataclass
class State:
    node: Node
    # 入力可能な Edge, その Edge 内での entry の位置, その entry 内での input の位置
    available_edges: Tuple[Tuple[Edge, int, int], ...]
    # これまでに入力が完了した Entry
    passed_entries: Tuple[Entry, ...]

    @property
    def finished(self) -> bool:
        return bool(self.node.finished)

    @property
    def inputted(self) -> str:
        next = 0
        inputted = []
        for e in self.passed_entries:
            inputted.append(e.input[next:])
            next = len(e.next)
        if self.available_edges:
            edge, entry_index, input_index = self.available_edges[0]
            inputted.append(edge.entries[entry_index].input[next:input_index])
        return "".join(inputted)

    @property
    def outputted(self) -> str:
        outputted = []
        for e in self.passed_entries:
            outputted.append(e.output)
        return "".join(outputted)

    @classmethod
    def __input(cls, i: str, edge: Edge, entry_index: int, input_index: int, finished_entries=()):
        if not i or entry_index >= len(edge.entries):
            return bool(finished_entries), entry_index, input_index, finished_entries

        entry = edge.entries[entry_index]
        if entry.input[input_index:].startswith(i):
            if len(entry.input) == input_index + len(i):
                # entry.input の最後の文字を入力完了
                return cls.__input(entry.next, edge, entry_index + 1, 0, finished_entries + (entry,))
            else:
                # entry.input の途中の文字を入力完了
                return True, entry_index, input_index + len(i), finished_entries
        return False, entry_index, input_index, finished_entries

    def test(self, i: str) -> InputResult:
        new_available_edges: List[Tuple[Edge, int, int]] = []
        finished_entries: Tuple[Entry, ...] = ()
        for edge, entry_index, input_index in self.available_edges:
            succeeded, new_entry_index, new_input_index, tmp_finished_entries = \
                self.__input(i, edge, entry_index, input_index)
            if succeeded:
                finished_entries = tmp_finished_entries
                if len(edge.entries) == new_entry_index:
                    new_state = State(edge.next,
                                      tuple((e, 0, 0) for e in edge.next.next_edges),
                                      self.passed_entries + tmp_finished_entries)
                    return InputResult(True, new_state, tmp_finished_entries)
                else:
                    new_available_edges.append((edge, new_entry_index, new_input_index))
        if new_available_edges:
            new_passed_entries = self.passed_entries + finished_entries
            new_state = State(self.node,
                              tuple(new_available_edges),
                              new_passed_entries)
            return InputResult(True, new_state, finished_entries)
        return InputResult(False, self, ())

    def __repr__(self):
        return str((id(self.node) % 10000, [(id(e[0]) % 10000, e[1], e[2]) for e in self.available_edges]))


@dataclass
class Automaton:
    _start_node: Node
    _end_node: Node
    _state: State = dataclasses.field(init=False)

    def __post_init__(self):
        self.reset()

    @property
    def inputted(self) -> str:
        return self._state.inputted

    @property
    def outputted(self) -> str:
        return self._state.outputted

    def test(self, i: str) -> InputResult:
        """内部状態を変更せずに、入力を与えたときに得られる結果を返す
        """
        return self._state.test(i)

    def input(self, i: str) -> InputResult:
        """入力して内部状態を進め、そのときに得られる結果を返す
        """
        result = self.test(i)
        self._state = result.new_state
        return result

    def reset(self):
        """内部状態をリセットする
        """
        i = self._start_node
        self._state = State(i, [(e, 0, 0) for e in i.next_edges], ())

    def inputtable(self) -> List[str]:
        """次の状態に遷移可能な入力リストを返す
        """
        pass

    def head_print_str(self) -> str:
        """入力済みの表示文字列を返す
        """
        pass

    def head_input_str(self) -> str:
        """入力済みの入力文字列を返す
        """
        pass

    def tail_print_str(self) -> str:
        """残りの表示文字列を返す
        """
        pass

    def tail_input_str(self) -> str:
        """残りの入力文字列を返す

        残りの入力文字列は複数のパターンがありうるが、もっともらしいものを1つ選択して返す
        """
        pass
