"""测试 structure_formatter 的 compare_structures 方法"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.structure_formatter import structure_formatter


def test_compare_structures():
    """测试结构对比功能"""

    # 模拟旧的结构
    old_structure = {
        "method": "rule_engine",
        "overall_confidence": 0.85,
        "paragraphs": [
            {
                "index": 0,
                "text": "第一题",
                "content_type": "body",
                "content_type_name": "正文",
                "confidence": 0.7,
            },
            {
                "index": 1,
                "text": "A. 选项一",
                "content_type": "body",
                "content_type_name": "正文",
                "confidence": 0.6,
            },
            {
                "index": 2,
                "text": "B. 选项二",
                "content_type": "option",
                "content_type_name": "选项",
                "confidence": 0.9,
            },
        ],
    }

    # 模拟新的结构
    new_structure = {
        "method": "llm",
        "overall_confidence": 0.92,
        "paragraphs": [
            {
                "index": 0,
                "text": "第一题",
                "content_type": "question_number",
                "content_type_name": "题号",
                "confidence": 0.95,
                "reason": "用户意见：段落0应该是题号",
            },
            {
                "index": 1,
                "text": "A. 选项一",
                "content_type": "option",
                "content_type_name": "选项",
                "confidence": 0.98,
                "reason": "系统判断：以A.开头，符合选项模式",
            },
            {
                "index": 2,
                "text": "B. 选项二",
                "content_type": "option",
                "content_type_name": "选项",
                "confidence": 0.99,
            },
        ],
    }

    # 调用对比方法
    changes = structure_formatter.compare_structures(old_structure, new_structure)

    # 验证结果
    print(f"\n✅ 测试通过！检测到 {len(changes)} 处变化：\n")
    for change in changes:
        print(
            f"  段落#{change['index']}: {change['old_type_name']} → {change['new_type_name']}"
        )
        print(f"    理由: {change['reason']}\n")

    # 断言
    assert len(changes) == 2, f"应该检测到2处变化，实际检测到{len(changes)}处"
    assert changes[0]["index"] == 0
    assert changes[0]["old_type"] == "body"
    assert changes[0]["new_type"] == "question_number"
    assert changes[1]["index"] == 1
    assert changes[1]["old_type"] == "body"
    assert changes[1]["new_type"] == "option"

    print("✅ 所有断言通过！")


def test_compare_no_changes():
    """测试无变化的情况"""

    structure = {
        "method": "rule_engine",
        "overall_confidence": 0.9,
        "paragraphs": [
            {
                "index": 0,
                "text": "测试",
                "content_type": "body",
                "content_type_name": "正文",
                "confidence": 0.8,
            }
        ],
    }

    changes = structure_formatter.compare_structures(structure, structure)

    assert len(changes) == 0, "相同结构应该没有变化"
    print("✅ 无变化测试通过！")


if __name__ == "__main__":
    try:
        test_compare_structures()
        test_compare_no_changes()
        print("\n🎉 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
