"""字体名和颜色工具函数"""

from difflib import SequenceMatcher
from typing import Dict, Tuple

# 字体别名映射
FONT_ALIASES: Dict[str, str] = {
    "SimSun": "宋体",
    "宋体": "SimSun",
    "SimHei": "黑体",
    "黑体": "SimHei",
    "KaiTi": "楷体",
    "楷体": "KaiTi",
    "FangSong": "仿宋",
    "仿宋": "FangSong",
    "Microsoft YaHei": "微软雅黑",
    "微软雅黑": "Microsoft YaHei",
    "STSong": "华文宋体",
    "STHeiti": "华文黑体",
    "STKaiti": "华文楷体",
    "STFangsong": "华文仿宋",
    "Arial": "Arial",
    "Times New Roman": "Times New Roman",
    "Courier New": "Courier New",
    "Calibri": "Calibri",
    "Cambria": "Cambria",
}


def normalize_font_name(name: str) -> str:
    """规范化字体名：去除子集前缀、处理别名"""
    if not name:
        return "宋体"
    # 去除子集前缀如 "AAAAAA+SimSun" -> "SimSun"
    if "+" in name:
        name = name.split("+")[-1]
    # 去除多余空格
    name = name.strip()
    return name


def fuzzy_font_match(font_a: str, font_b: str) -> float:
    """模糊匹配两个字体名，返回 [0.0, 1.0] 的相似度"""
    a = normalize_font_name(font_a)
    b = normalize_font_name(font_b)

    # 完全相同
    if a == b:
        return 1.0

    # 别名匹配
    if FONT_ALIASES.get(a) == b or FONT_ALIASES.get(b) == a:
        return 0.95

    # 大小写不敏感匹配
    if a.lower() == b.lower():
        return 0.95

    # 模糊匹配
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_color(color: str) -> str:
    """规范化颜色值：统一为6位大写十六进制"""
    if not color:
        return "000000"

    color = color.strip().lstrip("#")

    # 处理3位简写
    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    # 处理带alpha的8位格式
    if len(color) == 8:
        color = color[2:]  # 取后6位

    # 统一大写
    color = color.upper()

    # 确保是有效的6位十六进制
    if len(color) != 6:
        return "000000"

    try:
        int(color, 16)
        return color
    except ValueError:
        return "000000"


def color_similarity(color_a: str, color_b: str) -> float:
    """计算两个颜色的相似度 [0.0, 1.0]"""
    a = normalize_color(color_a)
    b = normalize_color(color_b)

    if a == b:
        return 1.0

    # 解析RGB分量
    try:
        r1, g1, b1 = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
        r2, g2, b2 = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    except ValueError:
        return 0.0

    # 计算欧氏距离归一化
    max_dist = 255 * 3**0.5
    dist = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
    return max(0.0, 1.0 - dist / max_dist)


def numeric_match(val_a, val_b, tolerance: float = 0.01) -> float:
    """比较两个数值的匹配度，支持容差"""
    if val_a is None and val_b is None:
        return 1.0
    if val_a is None or val_b is None:
        return 0.0

    try:
        a = float(val_a)
        b = float(val_b)
    except (ValueError, TypeError):
        return 0.0

    if a == b:
        return 1.0

    # 相对误差
    max_val = max(abs(a), abs(b), 0.001)
    diff = abs(a - b) / max_val

    if diff <= tolerance:
        return 1.0
    return max(0.0, 1.0 - diff)


def list_similarity(list_a, list_b) -> float:
    """比较两个数值列表的相似度（长度+值）"""
    if not list_a and not list_b:
        return 1.0
    if not list_a or not list_b:
        return 0.0

    # 长度匹配
    len_score = min(len(list_a), len(list_b)) / max(len(list_a), len(list_b))

    # 值匹配（按位置对齐）
    min_len = min(len(list_a), len(list_b))
    val_scores = []
    for i in range(min_len):
        val_scores.append(numeric_match(list_a[i], list_b[i]))

    val_score = sum(val_scores) / len(val_scores) if val_scores else 0.0

    return (len_score + val_score) / 2
