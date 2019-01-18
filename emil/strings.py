# coding: utf-8


def split_suffixes(text: str, max_length: int):
    if not text or max_length <= 0:
        return []
    max_length = min(max_length, len(text))
    return [text[-(i+1):] for i in range(max_length)]


def split_prefixes(text: str, max_length: int):
    if not text or max_length <= 0:
        return []
    max_length = min(max_length, len(text))
    return [text[:i+1] for i in range(max_length)]
