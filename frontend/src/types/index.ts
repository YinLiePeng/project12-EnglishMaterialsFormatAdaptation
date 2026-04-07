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

/** 样式详情 */
export interface AppliedStyle {
  key: string;
  name: string;
  font: {
    name: string;
    size: number;
    bold: boolean;
    color?: string;
  };
  format: {
    alignment: string;
    line_spacing: number;
    space_before?: number;
    space_after?: number;
    first_line_indent?: number;
  };
}

/** 段落结构识别结果 */
export interface ParagraphStructure {
  index: number;
  text: string;
  content_type: string;
  content_type_name: string;
  confidence: number;
  applied_style: AppliedStyle;
  reason?: string;
}

/** 文章结构分析 */
export interface StructureAnalysis {
  method: 'rule_engine' | 'llm';
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
