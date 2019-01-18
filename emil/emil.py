# coding: utf-8
from __future__ import annotations
from typing import Optional, List, Dict, Set
import dataclasses
from dataclasses import dataclass
from . import builder, automaton


@dataclass
class Emil:
    rule: builder.Rule

    @staticmethod
    def from_file(rule_file: str) -> Emil:
        pass

    def build(self, word: str) -> automaton.Automaton:
        pass
