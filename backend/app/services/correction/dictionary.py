"""词典加载与查询模块"""

import json
from pathlib import Path
from typing import Set, Optional
from functools import lru_cache


class Dictionary:
    """词典类 - 用于拼写验证"""

    def __init__(self, name: str):
        self.name = name
        self.words: Set[str] = set()

    def load_from_file(self, file_path: str):
        """从JSON文件加载词典"""
        path = Path(file_path)
        if not path.exists():
            print(f"词典文件不存在: {file_path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                words_list = data.get("words", [])
                self.words = set(word.lower() for word in words_list)
                print(f"已加载词典 {self.name}: {len(self.words)} 个单词")
        except Exception as e:
            print(f"加载词典失败: {e}")

    def contains(self, word: str) -> bool:
        """检查单词是否在词典中"""
        return word.lower() in self.words

    def __contains__(self, word: str) -> bool:
        return self.contains(word)

    def __len__(self) -> int:
        return len(self.words)


class DictionaryManager:
    """词典管理器"""

    def __init__(self, dictionary_dir: str = None):
        if dictionary_dir is None:
            # 获取backend目录下的core/dictionary路径
            backend_dir = Path(__file__).parent.parent.parent.parent
            dictionary_dir = str(backend_dir / "core" / "dictionary")
        self.dictionary_dir = Path(dictionary_dir)
        self.oxford = Dictionary("牛津词典")
        self.gaokao = Dictionary("考纲词汇")

    def load_all(self):
        """加载所有词典"""
        oxford_path = self.dictionary_dir / "oxford.json"
        gaokao_path = self.dictionary_dir / "gaokao.json"

        if oxford_path.exists():
            self.oxford.load_from_file(str(oxford_path))
        else:
            print(f"牛津词典文件不存在: {oxford_path}")

        if gaokao_path.exists():
            self.gaokao.load_from_file(str(gaokao_path))
        else:
            print(f"考纲词汇文件不存在: {gaokao_path}")

    def is_valid_spelling(self, word: str) -> bool:
        """验证拼写是否正确（双重验证）

        一个单词要被认为是正确的，需要在至少一个词典中存在
        """
        word_lower = word.lower()
        return self.oxford.contains(word_lower) or self.gaokao.contains(word_lower)

    def can_auto_correct(self, word: str) -> bool:
        """检查是否可以自动修正

        一个单词可以自动修正，需要在两个词典中都存在
        """
        word_lower = word.lower()
        return self.oxford.contains(word_lower) and self.gaokao.contains(word_lower)


# 全局词典管理器实例
dictionary_manager = DictionaryManager()
