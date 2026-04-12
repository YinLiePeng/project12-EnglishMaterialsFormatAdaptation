/** API响应类型 */
export interface ApiResponse<T = unknown> {
  code: number;
  message?: string;
  data: T;
}

/** 预设样式 */
export interface PresetStyle {
  id: string;
  name: string;
  description: string;
  config?: StyleConfig;
  preserve_format?: boolean;
  category?: string;
}

/** 样式配置 */
export interface StyleConfig {
  name: string;
  description: string;
  page: PageSettings;
  heading1: TextStyle;
  heading2: TextStyle;
  heading3: TextStyle;
  body: TextStyle;
  question_number: TextStyle;
  option: TextStyle;
}

/** 页面设置 */
export interface PageSettings {
  width: number;
  height: number;
  margin_top: number;
  margin_bottom: number;
  margin_left: number;
  margin_right: number;
}

/** 文本样式 */
export interface TextStyle {
  font: {
    name: string;
    size: number;
    bold: boolean;
    color: string;
  };
  format: {
    alignment: string;
    line_spacing: number;
    space_before?: number;
    space_after?: number;
    first_line_indent?: number;
    left_indent?: number;
  };
}

/** 样式元素 */
export interface StyleElement {
  font: {
    name: string;
    size: number;
    bold: boolean;
    color: string;
  };
  format: {
    alignment: string;
    line_spacing: number;
    space_before?: number;
    space_after?: number;
    first_line_indent?: number;
    left_indent?: number;
  };
}

/** 段落原始样式（从原文档提取） */
export interface OriginalStyle {
  font_name: string;
  font_size: number;
  font_bold: boolean;
  font_italic: boolean;
  font_underline: boolean;
  font_color: string;
  alignment: string;
  line_spacing: number | null;
  line_spacing_rule: string | null;
  space_before: number | null;
  space_after: number | null;
  first_line_indent: number | null;
  left_indent: number | null;
}

/** 样式详情 */
export interface AppliedStyle {
  key: string;
  name: string;
  font: {
    name: string;
    size: number;
    bold: boolean;
    color?: string;
    italic?: boolean;
    underline?: boolean;
  };
  format: {
    alignment: string;
    line_spacing: number;
    line_spacing_rule?: string | null;
    space_before?: number;
    space_after?: number;
    first_line_indent?: number;
    left_indent?: number;
  };
}

/** 段落结构识别结果 */
export interface ParagraphStructure {
  index: number;
  text: string;
  content_type: string;
  content_type_name: string;
  confidence: number;
  original_style: OriginalStyle;
  applied_style: AppliedStyle;
  reason?: string;
}

/** 文章结构分析 */
export interface StructureAnalysis {
  method: 'rule_engine' | 'llm';
  style_map?: Record<string, AppliedStyle>;
  overall_confidence: number;
  paragraphs: ParagraphStructure[];
  summary?: string;
}

/** 任务状态 */
export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  layout_mode: string;
  preset_style: string;
  enable_llm?: number;
  input_filename: string;
  output_filename: string | null;
  processing_time: number | null;
  error_message: string | null;
  error_code: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  structure_analysis?: StructureAnalysis;
}

/** 上传参数 */
export interface UploadParams {
  file: File;
  template?: File;
  layout_mode: 'none' | 'empty' | 'complete';
  preset_style?: string;
  enable_cleaning?: boolean;
  enable_correction?: boolean;
}

/** 测试用例提交参数 */
export interface TestCaseSubmitParams {
  original_file: File;
  feedback_description: string;
  problem_types: string[];
  output_file?: File;
  contact_info?: string;
  task_id?: string;
}

/** 测试用例 */
export interface TestCase {
  id: string;
  original_filename: string;
  output_filename: string | null;
  feedback_description: string;
  problem_types: string[];
  contact_info: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
  task_id: string | null;
}

/** 测试用例详情（包含更多信息） */
export interface TestCaseDetail extends TestCase {
  original_file_path: string;
  output_file_path: string | null;
  admin_notes: string | null;
  resolved_at: string | null;
}

/** 测试用例列表响应 */
export interface TestCaseListResponse {
  total: number;
  testcases: TestCase[];
  page: number;
  page_size: number;
}

/** 任务列表响应 */
export interface TaskListResponse {
  total: number;
  tasks: TaskStatus[];
  page: number;
  page_size: number;
}

/** 任务筛选条件 */
export interface TaskFilters {
  status?: string;
  filename?: string;
  layout_mode?: string;
  start_date?: string;
  end_date?: string;
}

/** 任务排序选项 */
export interface TaskSort {
  by: 'created_at' | 'processing_time' | 'input_filename';
  order: 'asc' | 'desc';
}

/** 任务统计数据 */
export interface TaskStatistics {
  total: number;
  status_stats: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  today_count: number;
  week_count: number;
  success_rate: number;
  avg_processing_time: number;
}

/** 批量删除响应 */
export interface BatchDeleteResponse {
  deleted_count: number;
  deleted_files: number;
  skipped_count?: number;
}

// ==================== 智能修正功能类型 ====================

/** 段落更新 */
export interface ParagraphUpdate {
  index: number;
  content_type: string;
}

/** 快速修正请求 */
export interface QuickCorrectionRequest {
  paragraph_updates: ParagraphUpdate[];
  user_feedback?: string;
  regenerate?: boolean;
}

/** 快速修正响应 */
export interface QuickCorrectionResponse {
  updated_count: number;
  structure_analysis: StructureAnalysis;
}

/** AI识别请求 */
export interface AIRecognizeRequest {
  user_feedback?: string;
  paragraph_updates?: ParagraphUpdate[];
  mode: 'preview' | 'apply';
}

/** 修正变化 */
export interface CorrectionChange {
  index: number;
  old_type: string;
  old_type_name: string;
  new_type: string;
  new_type_name: string;
  reason: string;
}

/** AI识别预览响应 */
export interface AIRecognizePreviewResponse {
  mode: 'preview';
  changes: CorrectionChange[];
  structure_analysis: StructureAnalysis;
}

/** AI识别应用响应 */
export interface AIRecognizeApplyResponse {
  mode: 'apply';
  applied_count: number;
  structure_analysis: StructureAnalysis;
}

/** 重新生成文档响应 */
export interface RegenerateDocumentResponse {
  output_filename: string;
  download_url: string;
}

/** 段落编辑状态 */
export interface ParagraphEdit {
  paragraphIndex: number;
  originalType: string;
  newType: string;
}

/** AI识别响应类型（联合类型） */
export type AIRecognizeResponse = AIRecognizePreviewResponse | AIRecognizeApplyResponse;

// ==================== LLM 流式处理 SSE 事件类型 ====================

/** SSE 进度事件 */
export interface SSEProgressEvent {
  stage: 'parsing' | 'cleaning' | 'correcting' | 'recognizing' | 'formatting';
  message: string;
}

/** SSE 文本块事件 */
export interface SSEChunkEvent {
  content: string;
}

/** SSE 分析结果事件 */
export interface SSEAnalysisEvent {
  structure: StructureAnalysis;
  raw_output: string;
  method: 'llm';
}

/** SSE 完成事件 */
export interface SSEDoneEvent {
  status: 'completed';
  processing_time: number;
  output_filename: string | null;
}

/** SSE 错误事件 */
export interface SSEErrorEvent {
  code: string;
  message: string;
}

/** SSE 事件回调集合 */
export interface SSECallbacks {
  onProgress?: (data: SSEProgressEvent) => void;
  onChunk?: (data: SSEChunkEvent) => void;
  onAnalysis?: (data: SSEAnalysisEvent) => void;
  onDone?: (data: SSEDoneEvent) => void;
  onError?: (data: SSEErrorEvent) => void;
}
