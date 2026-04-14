"""Word修订和批注功能 - 基于docx-editor库"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from docx_editor import Document


class RevisionEditor:
    """修订编辑器 - 封装docx-editor库"""

    def __init__(self, file_path: str, author: str = "格式适配工具"):
        self.file_path = Path(file_path)
        self.author = author
        self.doc: Optional[Document] = None

    def open(self):
        """打开文档"""
        self.doc = Document.open(str(self.file_path), author=self.author)
        return self

    def close(self, cleanup: bool = True):
        """关闭文档"""
        if self.doc:
            self.doc.close(cleanup=cleanup)
            self.doc = None

    def save(self, output_path: str = None):
        """保存文档"""
        if self.doc:
            if output_path:
                self.doc.save(output_path)
            else:
                self.doc.save()
        return self

    def replace_text(self, find: str, replace_with: str, occurrence: int = 0) -> int:
        """替换文本（带修订标记）

        Args:
            find: 要查找的文本
            replace_with: 替换后的文本
            occurrence: 第几个匹配项（0表示第一个）

        Returns:
            修订ID
        """
        if not self.doc:
            raise RuntimeError("文档未打开")

        try:
            return self.doc.replace(find, replace_with, occurrence)
        except Exception as e:
            print(f"替换失败: {e}")
            return -1

    def add_comment(self, anchor_text: str, comment_text: str) -> int:
        """添加批注

        Args:
            anchor_text: 批注锚定的文本
            comment_text: 批注内容

        Returns:
            批注ID
        """
        if not self.doc:
            raise RuntimeError("文档未打开")

        try:
            return self.doc.add_comment(anchor_text, comment_text)
        except Exception as e:
            print(f"添加批注失败: {e}")
            return -1

    def list_revisions(self) -> List[Dict[str, Any]]:
        """列出所有修订"""
        if not self.doc:
            raise RuntimeError("文档未打开")

        try:
            revisions = self.doc.list_revisions()
            return [
                {
                    "id": r.id,
                    "type": r.type,
                    "author": r.author,
                    "date": r.date,
                    "text": r.text,
                }
                for r in revisions
            ]
        except Exception as e:
            print(f"获取修订列表失败: {e}")
            return []

    def count_revisions(self) -> int:
        """统计修订数量"""
        return len(self.list_revisions())

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class RevisionGenerator:
    """修订生成器 - 根据纠错结果生成修订和批注"""

    def __init__(self, file_path: str, author: str = "格式适配工具"):
        self.file_path = file_path
        self.author = author

    def apply_corrections(self, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用纠错结果到文档

        Args:
            corrections: 纠错列表，每个包含:
                - original: 原文
                - replacement: 修正后文本（可选）
                - action: "replace" 或 "annotate"
                - reason: 修改原因

        Returns:
            处理结果统计
        """
        results = {
            "success": True,
            "revision_count": 0,
            "comment_count": 0,
            "errors": [],
        }

        with RevisionEditor(self.file_path, self.author) as editor:
            for correction in corrections:
                original = correction.get("original", "")
                replacement = correction.get("replacement", "")
                action = correction.get("action", "annotate")
                reason = correction.get("reason", "")

                if not original:
                    continue

                try:
                    if action == "replace" and replacement:
                        # 应用修订（替换）
                        revision_id = editor.replace_text(original, replacement)
                        if revision_id >= 0:
                            results["revision_count"] += 1
                        else:
                            results["errors"].append(f"替换失败: {original}")
                    else:
                        # 添加批注
                        comment_text = f"疑似问题：{reason}" if reason else "疑似问题"
                        comment_id = editor.add_comment(original, comment_text)
                        if comment_id >= 0:
                            results["comment_count"] += 1
                        else:
                            results["errors"].append(f"批注失败: {original}")

                except Exception as e:
                    results["errors"].append(f"处理 '{original}' 时出错: {str(e)}")

        return results


def apply_revisions_to_docx(
    file_path: str,
    corrections: List[Dict[str, Any]],
    author: str = "格式适配工具",
    output_path: str = None,
) -> Dict[str, Any]:
    """将修订应用到DOCX文件的便捷函数

    Args:
        file_path: 输入文件路径
        corrections: 纠错结果列表
        author: 修订作者
        output_path: 输出文件路径（可选）

    Returns:
        处理结果
    """
    generator = RevisionGenerator(file_path, author)
    return generator.apply_corrections(corrections)
