export const CONTENT_TYPE_COLORS: Record<string, string> = {
  title: 'bg-purple-100 text-purple-800 border-purple-300',
  heading: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  question_number: 'bg-blue-100 text-blue-800 border-blue-300',
  option: 'bg-green-100 text-green-800 border-green-300',
  body: 'bg-gray-100 text-gray-800 border-gray-300',
  answer: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  analysis: 'bg-orange-100 text-orange-800 border-orange-300',
};

export const CONTENT_TYPE_HIGHLIGHT: Record<string, string> = {
  title: 'ring-2 ring-purple-400 bg-purple-50',
  heading: 'ring-2 ring-indigo-400 bg-indigo-50',
  question_number: 'ring-2 ring-blue-400 bg-blue-50',
  option: 'ring-2 ring-green-400 bg-green-50',
  body: 'ring-2 ring-gray-400 bg-gray-50',
  answer: 'ring-2 ring-yellow-400 bg-yellow-50',
  analysis: 'ring-2 ring-orange-400 bg-orange-50',
};

export const CONTENT_TYPE_OPTIONS = [
  { value: 'title', label: '主标题' },
  { value: 'heading', label: '子标题' },
  { value: 'question_number', label: '题号' },
  { value: 'option', label: '选项' },
  { value: 'body', label: '正文' },
  { value: 'answer', label: '答案' },
  { value: 'analysis', label: '解析' },
];

export const CONTENT_TYPE_NAMES: Record<string, string> = {
  title: '主标题',
  heading: '子标题',
  question_number: '题号',
  option: '选项',
  body: '正文',
  answer: '答案',
  analysis: '解析',
};

export const ALIGNMENT_LABELS: Record<string, string> = {
  left: '左对齐',
  center: '居中',
  right: '右对齐',
  justify: '两端对齐',
};

export function formatStyleSummary(style: any): string {
  if (!style) return '';
  const parts: string[] = [];
  const font = style.font;
  const fmt = style.format;

  if (font?.name) parts.push(font.name);
  if (font?.size) parts.push(`${font.size}pt`);
  if (font?.bold) parts.push('加粗');
  if (font?.italic) parts.push('斜体');
  if (font?.underline) parts.push('下划线');
  if (fmt?.alignment) parts.push(ALIGNMENT_LABELS[fmt.alignment] || fmt.alignment);
  if (fmt?.line_spacing) parts.push(`行距:${fmt.line_spacing}${fmt.line_spacing_rule === 'exact' ? 'pt固定' : '倍'}`);
  if (fmt?.first_line_indent && fmt.first_line_indent > 0) parts.push(`首行缩进:${fmt.first_line_indent}字符`);
  if (fmt?.left_indent && fmt.left_indent > 0) parts.push(`左缩进:${fmt.left_indent}`);
  if (fmt?.space_before && fmt.space_before > 0) parts.push(`段前:${fmt.space_before}pt`);
  if (fmt?.space_after && fmt.space_after > 0) parts.push(`段后:${fmt.space_after}pt`);

  return parts.join(' ');
}
