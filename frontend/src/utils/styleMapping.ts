import type { StyleConfig } from '../types';

/**
 * 字体名称映射
 * 将中文字体名映射为CSS字体栈
 */
export const FONT_MAPPING: Record<string, string> = {
  '黑体': '"SimHei", "Microsoft YaHei", "PingFang SC", sans-serif',
  '宋体': '"SimSun", "Songti SC", "FangSong", serif',
  '楷体': '"KaiTi", "Kaiti SC", "STKaiti", serif',
  'Times New Roman': '"Times New Roman", Times, serif',
  'Arial': '"Arial", Helvetica, sans-serif',
  'Calibri': '"Calibri", sans-serif',
  'Verdana': '"Verdana", sans-serif',
};

/**
 * 将字体名映射为 CSS 字体栈
 */
export function mapFontName(name: string | undefined): string {
  if (!name) return FONT_MAPPING['宋体'];
  return FONT_MAPPING[name] || name;
}

/**
 * 计算行距 CSS 值
 * - auto 模式：直接作为倍数
 * - exact / atLeast 模式：转为 pt 字符串
 */
export function mapLineSpacing(value: number | undefined, rule?: string): string | number {
  if (value === undefined || value === null) return 1.5;
  if (rule === 'exact' || rule === 'atLeast') return `${value}pt`;
  return value;
}

/**
 * 根据字体大小计算首行缩进 em 值
 * 后端 first_line_indent 单位为"字符数"（如 2.0 表示2个字符宽）
 * CSS 中 1em = 当前字体大小，1个中文字符 ≈ 1em
 */
export function indentToEm(charCount: number | undefined): string {
  if (!charCount) return '0';
  return `${charCount}em`;
}

/**
 * 对齐方式映射
 */
export const ALIGNMENT_MAPPING: Record<string, string> = {
  'left': 'left',
  'center': 'center',
  'right': 'right',
  'justify': 'justify',
};

/**
 * 对齐方式中文标签
 */
export const ALIGNMENT_LABEL: Record<string, string> = {
  'left': '左对齐',
  'center': '居中',
  'right': '右对齐',
  'justify': '两端对齐',
};

/**
 * pt转px
 * 1pt = 1.333px
 */
export function ptToPx(pt: number): string {
  return `${pt * 1.333}px`;
}

/**
 * 生成完整的CSS样式对象
 * @param styleConfig 样式配置
 * @returns CSS样式对象
 */
export function generateStyleCSS(styleConfig: StyleConfig) {
  return {
    // 标题1
    heading1: {
      fontFamily: FONT_MAPPING[styleConfig.heading1.font.name] || styleConfig.heading1.font.name,
      fontSize: ptToPx(styleConfig.heading1.font.size),
      fontWeight: styleConfig.heading1.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.heading1.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.heading1.format.alignment] || 'left',
      lineHeight: styleConfig.heading1.format.line_spacing,
      marginBottom: ptToPx(styleConfig.heading1.format.space_after || 0),
    },

    // 标题2
    heading2: {
      fontFamily: FONT_MAPPING[styleConfig.heading2.font.name] || styleConfig.heading2.font.name,
      fontSize: ptToPx(styleConfig.heading2.font.size),
      fontWeight: styleConfig.heading2.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.heading2.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.heading2.format.alignment] || 'left',
      lineHeight: styleConfig.heading2.format.line_spacing,
      marginTop: ptToPx(styleConfig.heading2.format.space_before || 0),
      marginBottom: ptToPx(styleConfig.heading2.format.space_after || 0),
    },

    // 标题3
    heading3: {
      fontFamily: FONT_MAPPING[styleConfig.heading3.font.name] || styleConfig.heading3.font.name,
      fontSize: ptToPx(styleConfig.heading3.font.size),
      fontWeight: styleConfig.heading3.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.heading3.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.heading3.format.alignment] || 'left',
      lineHeight: styleConfig.heading3.format.line_spacing,
      marginTop: ptToPx(styleConfig.heading3.format.space_before || 0),
      marginBottom: ptToPx(styleConfig.heading3.format.space_after || 0),
    },

    // 正文
    body: {
      fontFamily: FONT_MAPPING[styleConfig.body.font.name] || styleConfig.body.font.name,
      fontSize: ptToPx(styleConfig.body.font.size),
      fontWeight: styleConfig.body.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.body.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.body.format.alignment] || 'left',
      lineHeight: styleConfig.body.format.line_spacing,
      textIndent: styleConfig.body.format.first_line_indent
        ? `${styleConfig.body.format.first_line_indent * 2}em`
        : '0',
      marginTop: ptToPx(styleConfig.body.format.space_before || 0),
      marginBottom: ptToPx(styleConfig.body.format.space_after || 0),
    },

    // 题号
    questionNumber: {
      fontFamily: FONT_MAPPING[styleConfig.question_number.font.name] || styleConfig.question_number.font.name,
      fontSize: ptToPx(styleConfig.question_number.font.size),
      fontWeight: styleConfig.question_number.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.question_number.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.question_number.format.alignment] || 'left',
      lineHeight: styleConfig.question_number.format.line_spacing,
    },

    // 选项
    option: {
      fontFamily: FONT_MAPPING[styleConfig.option.font.name] || styleConfig.option.font.name,
      fontSize: ptToPx(styleConfig.option.font.size),
      fontWeight: styleConfig.option.font.bold ? 'bold' : 'normal',
      color: `#${styleConfig.option.font.color}`,
      textAlign: ALIGNMENT_MAPPING[styleConfig.option.format.alignment] || 'left',
      lineHeight: styleConfig.option.format.line_spacing,
    },
  };
}

/**
 * 生成A4纸张的容器样式
 */
export function generatePaperStyles(pageSettings: {
  width: number;
  height: number;
  margin_top: number;
  margin_bottom: number;
  margin_left: number;
  margin_right: number;
}) {
  return {
    width: `${pageSettings.width}cm`,
    minHeight: `${pageSettings.height}cm`,
    paddingTop: `${pageSettings.margin_top}cm`,
    paddingBottom: `${pageSettings.margin_bottom}cm`,
    paddingLeft: `${pageSettings.margin_left}cm`,
    paddingRight: `${pageSettings.margin_right}cm`,
  };
}
