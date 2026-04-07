"""预设排版样式配置

基于《中小学英语教学资料基础排版规范研究报告》设计的8套预设排版方案。

方案说明：
1. 通用排版 - 兼顾美观与通用性，适用于所有学段的日常教学资料
2. 小学低年级护眼版 - 1-3年级，大字号宽行距
3. 小学高年级版 - 4-6年级，适中字号行距
4. 初中通用版 - 初中各年级，符合国标规范
5. 高中通用版 - 高中各年级，紧凑高效
6. 模拟试卷版 - 各类英语模拟考试，单倍行距节省空间
7. 专题讲义版 - 知识梳理、专题讲解
8. 作文范文版 - 英语作文范文、写作指导
"""

from typing import Dict, Any


def _create_style(
    name: str,
    description: str,
    heading1_font: Dict,
    heading1_format: Dict,
    heading2_font: Dict,
    heading2_format: Dict,
    heading3_font: Dict,
    heading3_format: Dict,
    body_font: Dict,
    body_format: Dict,
    question_number_font: Dict,
    question_number_format: Dict,
    option_font: Dict,
    option_format: Dict,
    page: Dict = None,
) -> Dict[str, Any]:
    """创建样式配置的辅助函数"""
    if page is None:
        page = {
            "width": 21.0,
            "height": 29.7,
            "margin_top": 2.54,
            "margin_bottom": 2.54,
            "margin_left": 2.54,
            "margin_right": 2.54,
        }

    return {
        "name": name,
        "description": description,
        "page": page,
        "heading1": {"font": heading1_font, "format": heading1_format},
        "heading2": {"font": heading2_font, "format": heading2_format},
        "heading3": {"font": heading3_font, "format": heading3_format},
        "body": {"font": body_font, "format": body_format},
        "question_number": {
            "font": question_number_font,
            "format": question_number_format,
        },
        "option": {"font": option_font, "format": option_format},
    }


# ============================================================
# 方案一：通用排版（兼顾美观与通用性）
# ============================================================
UNIVERSAL_STYLE = _create_style(
    name="通用排版",
    description="兼顾美观与通用性，适用于所有学段的日常教学资料",
    heading1_font={"name": "黑体", "size": 22.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.5, "space_after": 12.0},
    heading2_font={"name": "黑体", "size": 16.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    heading3_font={"name": "黑体", "size": 14.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 4.0,
        "space_after": 4.0,
    },
    body_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "justify",
        "line_spacing": 1.5,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Times New Roman",
        "size": 12.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.5, "left_indent": 2.0},
)


# ============================================================
# 方案二：小学低年级护眼版（1-3年级）
# ============================================================
PRIMARY_LOW_STYLE = _create_style(
    name="小学低年级护眼版",
    description="适用于小学1-3年级，大字号宽行距保护视力",
    page={
        "width": 21.0,
        "height": 29.7,
        "margin_top": 2.0,
        "margin_bottom": 2.0,
        "margin_left": 2.0,
        "margin_right": 2.0,
    },
    heading1_font={"name": "黑体", "size": 26.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 2.0, "space_after": 18.0},
    heading2_font={"name": "黑体", "size": 20.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "space_before": 12.0,
        "space_after": 12.0,
    },
    heading3_font={"name": "黑体", "size": 18.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "space_before": 8.0,
        "space_after": 8.0,
    },
    body_font={"name": "宋体", "size": 16.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "first_line_indent": 0.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Times New Roman",
        "size": 16.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 16.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 2.0, "left_indent": 3.0},
)


# ============================================================
# 方案三：小学高年级版（4-6年级）
# ============================================================
PRIMARY_HIGH_STYLE = _create_style(
    name="小学高年级版",
    description="适用于小学4-6年级，适中字号行距",
    heading1_font={"name": "黑体", "size": 24.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.5, "space_after": 12.0},
    heading2_font={"name": "黑体", "size": 18.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 8.0,
        "space_after": 8.0,
    },
    heading3_font={"name": "黑体", "size": 16.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    body_font={"name": "宋体", "size": 14.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "justify",
        "line_spacing": 1.5,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Times New Roman",
        "size": 14.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 14.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.5, "left_indent": 2.0},
)


# ============================================================
# 方案四：初中通用版
# ============================================================
JUNIOR_STYLE = _create_style(
    name="初中通用版",
    description="适用于初中各年级，符合国标规范",
    heading1_font={"name": "黑体", "size": 22.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.25, "space_after": 12.0},
    heading2_font={"name": "黑体", "size": 16.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    heading3_font={"name": "黑体", "size": 14.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "space_before": 4.0,
        "space_after": 4.0,
    },
    body_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "justify",
        "line_spacing": 1.25,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Arial",
        "size": 12.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.25, "left_indent": 2.0},
)


# ============================================================
# 方案五：高中通用版
# ============================================================
SENIOR_STYLE = _create_style(
    name="高中通用版",
    description="适用于高中各年级，紧凑高效",
    heading1_font={"name": "黑体", "size": 20.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.25, "space_after": 10.0},
    heading2_font={"name": "黑体", "size": 15.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    heading3_font={"name": "黑体", "size": 13.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "space_before": 4.0,
        "space_after": 4.0,
    },
    body_font={"name": "宋体", "size": 11.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "justify",
        "line_spacing": 1.25,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Arial",
        "size": 11.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.25,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 11.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.25, "left_indent": 2.0},
)


# ============================================================
# 方案六：模拟试卷版
# ============================================================
EXAM_STYLE = _create_style(
    name="模拟试卷版",
    description="适用于各类英语模拟考试，单倍行距节省空间",
    page={
        "width": 21.0,
        "height": 29.7,
        "margin_top": 2.5,
        "margin_bottom": 2.0,
        "margin_left": 2.0,
        "margin_right": 2.0,
    },
    heading1_font={"name": "Arial", "size": 20.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.0, "space_after": 12.0},
    heading2_font={"name": "Arial", "size": 14.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.0,
        "space_before": 8.0,
        "space_after": 4.0,
    },
    heading3_font={"name": "Arial", "size": 13.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.0,
        "space_before": 4.0,
        "space_after": 2.0,
    },
    body_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "left",
        "line_spacing": 1.0,
        "first_line_indent": 0.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Arial",
        "size": 12.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.0,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.0, "left_indent": 2.0},
)


# ============================================================
# 方案七：专题讲义版
# ============================================================
LECTURE_STYLE = _create_style(
    name="专题讲义版",
    description="适用于知识梳理、专题讲解，便于批注",
    heading1_font={"name": "黑体", "size": 22.0, "bold": True, "color": "000000"},
    heading1_format={"alignment": "center", "line_spacing": 1.5, "space_after": 12.0},
    heading2_font={"name": "黑体", "size": 16.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    heading3_font={"name": "黑体", "size": 14.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "space_before": 4.0,
        "space_after": 4.0,
    },
    body_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    body_format={
        "alignment": "justify",
        "line_spacing": 1.5,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Times New Roman",
        "size": 12.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 1.5,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 1.5, "left_indent": 2.0},
)


# ============================================================
# 方案八：作文范文版
# ============================================================
ESSAY_STYLE = _create_style(
    name="作文范文版",
    description="适用于英语作文范文、写作指导，2倍行距便于批注",
    heading1_font={
        "name": "Times New Roman",
        "size": 18.0,
        "bold": True,
        "color": "000000",
    },
    heading1_format={"alignment": "center", "line_spacing": 2.0, "space_after": 12.0},
    heading2_font={"name": "宋体", "size": 14.0, "bold": True, "color": "000000"},
    heading2_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "space_before": 6.0,
        "space_after": 6.0,
    },
    heading3_font={"name": "宋体", "size": 13.0, "bold": True, "color": "000000"},
    heading3_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "space_before": 4.0,
        "space_after": 4.0,
    },
    body_font={
        "name": "Times New Roman",
        "size": 12.0,
        "bold": False,
        "color": "000000",
    },
    body_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "first_line_indent": 2.0,
        "space_before": 0.0,
        "space_after": 0.0,
    },
    question_number_font={
        "name": "Times New Roman",
        "size": 12.0,
        "bold": True,
        "color": "000000",
    },
    question_number_format={
        "alignment": "left",
        "line_spacing": 2.0,
        "left_indent": 0.0,
    },
    option_font={"name": "宋体", "size": 12.0, "bold": False, "color": "000000"},
    option_format={"alignment": "left", "line_spacing": 2.0, "left_indent": 2.0},
)


# ============================================================
# 预设样式库
# ============================================================
PRESET_STYLES = {
    "universal": UNIVERSAL_STYLE,  # 通用排版
    "primary_low": PRIMARY_LOW_STYLE,  # 小学低年级
    "primary_high": PRIMARY_HIGH_STYLE,  # 小学高年级
    "junior": JUNIOR_STYLE,  # 初中通用
    "senior": SENIOR_STYLE,  # 高中通用
    "exam": EXAM_STYLE,  # 模拟试卷
    "lecture": LECTURE_STYLE,  # 专题讲义
    "essay": ESSAY_STYLE,  # 作文范文
}


def get_preset_style(style_id: str) -> Dict[str, Any]:
    """获取预设样式"""
    return PRESET_STYLES.get(style_id, UNIVERSAL_STYLE)


def get_style_mapping(preset_style: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """从预设样式中提取样式映射"""
    return {
        "heading1": preset_style.get("heading1", {}),
        "heading2": preset_style.get("heading2", {}),
        "heading3": preset_style.get("heading3", {}),
        "body": preset_style.get("body", {}),
        "question_number": preset_style.get("question_number", {}),
        "option": preset_style.get("option", {}),
    }


def get_preset_list() -> list:
    """获取预设样式列表（用于API返回）"""
    return [
        {"id": style_id, "name": style["name"], "description": style["description"]}
        for style_id, style in PRESET_STYLES.items()
    ]
