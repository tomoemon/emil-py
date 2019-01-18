# coding: utf-8
from setuptools import find_packages, setup


setup(
    name="emil",
    version='0.0.1',
    description='Google Japanese Input style automaton generator for typing games',
    author='tomoemon',
    packages=find_packages(),
    python_requires=">=3.7",
    # インストール時に PyPi から取得される外部パッケージ.
    install_requires=[],
    # ユーザーが指定した場合にインストールされる外部パッケージ.
    extras_require={},
    # コマンドが実行されたときのエントリーポイント.
    entry_points={}
)
