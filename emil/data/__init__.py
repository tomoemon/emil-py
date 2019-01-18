# -*- coding: utf-8 -*-
from pathlib import Path


def filepath(filename):
    return Path(__file__).resolve().parent / filename
