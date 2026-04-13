import axios from 'axios';
import type { 
  ApiResponse, 
  PresetStyle, 
  TaskStatus, 
  TestCaseSubmitParams, 
  TestCaseDetail,
  TestCaseListResponse,
  TaskListResponse,
  TaskFilters,
  TaskSort,
  TaskStatistics,
  BatchDeleteResponse,
  QuickCorrectionRequest,
  QuickCorrectionResponse,
  AIRecognizeRequest,
  AIRecognizePreviewResponse,
  AIRecognizeApplyResponse,
  RegenerateDocumentResponse,
  SSECallbacks,
  TemplatePreviewResponse
} from '../types';

// 创建axios实例
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

/** 获取模板预览（用于标记位选择） */
export async function getTemplatePreview(templateFile: File): Promise<TemplatePreviewResponse> {
  const formData = new FormData();
  formData.append('template', templateFile);
  const response = await api.post<ApiResponse<TemplatePreviewResponse>>('/upload/template-preview', formData, {
    timeout: 30000,
  });
  return response.data.data;
}

/** 获取预设样式列表 */
export async function getPresetStyles(): Promise<PresetStyle[]> {
  const response = await api.get<ApiResponse<PresetStyle[]>>('/upload/presets');
  return response.data.data;
}

/** 上传文件并创建任务 */
export async function uploadFile(params: {
  file: File;
  template?: File;
  layout_mode: string;
  preset_style?: string;
  enable_cleaning?: boolean;
  enable_correction?: boolean;
  use_llm?: boolean;
  marker_position?: string;
}): Promise<{ task_id: string }> {
  const formData = new FormData();
  formData.append('file', params.file);
  if (params.template) {
    formData.append('template', params.template);
  }
  formData.append('layout_mode', params.layout_mode);
  if (params.preset_style) {
    formData.append('preset_style', params.preset_style);
  }
  formData.append('enable_cleaning', params.enable_cleaning ? 'true' : 'false');
  formData.append('enable_correction', params.enable_correction ? 'true' : 'false');
  formData.append('use_llm', params.use_llm ? 'true' : 'false');
  if (params.marker_position) {
    formData.append('marker_position', params.marker_position);
  }

  const response = await api.post<ApiResponse<{ task_id: string }>>('/upload', formData);
  return response.data.data;
}

/** 查询任务状态 */
export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await api.get<ApiResponse<TaskStatus>>(`/tasks/${taskId}`);
  return response.data.data;
}

/** 获取任务列表 */
export async function getTaskList(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<TaskListResponse> {
  const response = await api.get<ApiResponse<TaskListResponse>>('/tasks', {
    params,
  });
  return response.data.data;
}

/** 取消任务 */
export async function cancelTask(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}`);
}

/** 获取下载URL */
export function getDownloadUrl(taskId: string): string {
  return `/api/v1/tasks/${taskId}/download`;
}

/** 提交测试用例 */
export async function submitTestCase(params: TestCaseSubmitParams): Promise<{ testcase_id: string }> {
  const formData = new FormData();
  formData.append('original_file', params.original_file);
  formData.append('feedback_description', params.feedback_description);
  formData.append('problem_types', JSON.stringify(params.problem_types));
  if (params.output_file) {
    formData.append('output_file', params.output_file);
  }
  if (params.contact_info) {
    formData.append('contact_info', params.contact_info);
  }
  if (params.task_id) {
    formData.append('task_id', params.task_id);
  }

  const response = await api.post<ApiResponse<{ testcase_id: string }>>('/testcase/submit', formData);
  return response.data.data;
}

/** 获取测试用例列表 */
export async function getTestCaseList(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<TestCaseListResponse> {
  const response = await api.get<ApiResponse<TestCaseListResponse>>('/testcase/list', {
    params,
  });
  return response.data.data;
}

/** 获取测试用例详情 */
export async function getTestCaseDetail(testcaseId: string): Promise<TestCaseDetail> {
  const response = await api.get<ApiResponse<TestCaseDetail>>(`/testcase/${testcaseId}`);
  return response.data.data;
}

/** 删除测试用例 */
export async function deleteTestCase(testcaseId: string): Promise<void> {
  await api.delete(`/testcase/${testcaseId}`);
}

/** 更新测试用例状态 */
export async function updateTestCaseStatus(
  testcaseId: string,
  status: string,
  adminNotes?: string
): Promise<void> {
  await api.put(`/testcase/${testcaseId}/status`, {
    status,
    admin_notes: adminNotes,
  });
}

/** 获取测试用例原始文件下载URL */
export function getTestCaseOriginalUrl(testcaseId: string): string {
  return `/api/v1/testcase/${testcaseId}/original`;
}

/** 获取测试用例输出文件下载URL */
export function getTestCaseOutputUrl(testcaseId: string): string {
  return `/api/v1/testcase/${testcaseId}/output`;
}

/** 批量删除任务 */
export async function deleteTasksBatch(taskIds: string[]): Promise<BatchDeleteResponse> {
  const response = await api.post<ApiResponse<BatchDeleteResponse>>('/tasks/delete-batch', taskIds);
  return response.data.data;
}

/** 获取任务统计数据 */
export async function getTaskStatistics(): Promise<TaskStatistics> {
  const response = await api.get<ApiResponse<TaskStatistics>>('/tasks/statistics/summary');
  return response.data.data;
}

/** 获取任务列表（支持高级筛选和排序） */
export async function getTaskListAdvanced(params: {
  page?: number;
  page_size?: number;
  filters?: TaskFilters;
  sort?: TaskSort;
}): Promise<TaskListResponse> {
  const queryParams: Record<string, string> = {};
  
  if (params.page) queryParams.page = params.page.toString();
  if (params.page_size) queryParams.page_size = params.page_size.toString();
  
  if (params.filters) {
    if (params.filters.status) queryParams.status = params.filters.status;
    if (params.filters.filename) queryParams.filename = params.filters.filename;
    if (params.filters.layout_mode) queryParams.layout_mode = params.filters.layout_mode;
    if (params.filters.start_date) queryParams.start_date = params.filters.start_date;
    if (params.filters.end_date) queryParams.end_date = params.filters.end_date;
  }
  
  if (params.sort) {
    queryParams.sort_by = params.sort.by;
    queryParams.sort_order = params.sort.order;
  }
  
  const response = await api.get<ApiResponse<TaskListResponse>>('/tasks', {
    params: queryParams,
  });
  return response.data.data;
}

// ==================== 智能修正功能API ====================

/** 快速修正 */
export async function quickCorrection(
  taskId: string,
  params: QuickCorrectionRequest
): Promise<QuickCorrectionResponse> {
  const response = await api.post<ApiResponse<QuickCorrectionResponse>>(
    `/tasks/${taskId}/quick-correction`,
    params
  );
  return response.data.data;
}

/** AI识别 */
export async function aiRecognize(
  taskId: string,
  params: AIRecognizeRequest
): Promise<AIRecognizePreviewResponse | AIRecognizeApplyResponse> {
  const response = await api.post<ApiResponse<AIRecognizePreviewResponse | AIRecognizeApplyResponse>>(
    `/tasks/${taskId}/ai-recognize`,
    params,
    { timeout: 120000 }
  );
  return response.data.data;
}

/** 重新生成文档 */
export async function regenerateDocument(
  taskId: string
): Promise<RegenerateDocumentResponse> {
  const response = await api.post<ApiResponse<RegenerateDocumentResponse>>(
    `/tasks/${taskId}/regenerate`
  );
  return response.data.data;
}

// ==================== LLM 流式处理 SSE ====================

/** 连接 LLM 流式处理端点 */
export function connectLLMStream(
  taskId: string,
  callbacks: SSECallbacks
): EventSource {
  const url = `/api/v1/tasks/${taskId}/llm-stream`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('progress', (e: MessageEvent) => {
    const data = JSON.parse(e.data);
    callbacks.onProgress?.(data);
  });

  eventSource.addEventListener('chunk', (e: MessageEvent) => {
    const data = JSON.parse(e.data);
    callbacks.onChunk?.(data);
  });

  eventSource.addEventListener('analysis', (e: MessageEvent) => {
    const data = JSON.parse(e.data);
    callbacks.onAnalysis?.(data);
  });

  eventSource.addEventListener('done', (e: MessageEvent) => {
    const data = JSON.parse(e.data);
    callbacks.onDone?.(data);
    eventSource.close();
  });

  eventSource.addEventListener('error', (e: MessageEvent) => {
    if (e.data) {
      try {
        const data = JSON.parse(e.data);
        callbacks.onError?.(data);
      } catch {
        callbacks.onError?.({ code: 'CONNECTION_ERROR', message: 'SSE连接异常' });
      }
    }
    eventSource.close();
  });

  eventSource.onerror = () => {
    callbacks.onError?.({ code: 'CONNECTION_ERROR', message: 'SSE连接断开' });
    eventSource.close();
  };

  return eventSource;
}
