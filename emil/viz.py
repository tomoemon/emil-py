# coding: utf-8
from __future__ import annotations
from typing import Optional, List, Dict, Set
from .automaton import Automaton, Node, Edge


"""automaton を受け取って graphviz で描画する
"""


def trace(previous: Node, output_stack: str, nodes: Dict[int, str], edges: Dict[int, Edge]):
    if id(previous) not in nodes:
        nodes[id(previous)] = f"n{len(output_stack)}"
    for e in previous.next_edges:
        if id(e) not in edges:
            edges[id(e)] = e
        trace(e.next, output_stack + "".join(et.output for et in e.entries), nodes, edges)


def str_edge(e: Edge) -> str:
    s = " | ".join(f"{entry.input}/{entry.output}/{entry.next}" for entry in e.entries)
    s = s.replace('"', '\"')
    return '"' + s + '"'


def render(auto: Automaton) -> str:
    nodes = {}
    edges = {}
    trace(auto._start_node, "", nodes, edges)
    nl = "\n"
    return f"""digraph graph_name {{
  graph [
    ranksep = 1.0
  ];

  //node define
  {
      (";"+nl+"  ").join(n for n in nodes.values()) + ";"
  }

  // edge define
  {
      (";"+nl+"  ").join(nodes[id(e.previous)] + " -> " + nodes[id(e.next)] + " [" + nl +
        "    label = " + str_edge(e) + nl +
        "  ]"
        for e in edges.values()) + ";"
  }
}}"""
