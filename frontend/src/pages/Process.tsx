import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadStore } from '../store/uploadStore';
import { useTaskPolling } from '../hooks/useTaskPolling';
import { connectLLMStream, getTaskStatus, getDownloadUrl, cancelTask } from '../services/api';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/EmptyState';
import type { TaskStatus, SSEProgressEvent, SSEAnalysisEvent, SSEDoneEvent, SSEErrorEvent, PdfInfo } from '../types';

// 阶段配置
const STAGE_CONFIG: Record<string, { label: string; description: string; defaultProgress: number }> = {
  parsing: { label: '解析文件', description: '提取PDF/DOCX中的文本、图片和表格', defaultProgress: 10 },
  cleaning: { label: '内容清洗', description: '过滤广告、水印、URL等垃圾内容', defaultProgress: 28 },
  correcting: { label: '内容纠错', description: '修正标点、拼写、格式问题', defaultProgress: 43 },
  recognizing: { label: '结构识别', description: '识别标题、题号、选项、正文等结构', defaultProgress: 60 },
  formatting: { label: '格式排版', description: '应用预设样式进行智能排版', defaultProgress: 80 },
  generating: { label: '生成文档', description: '生成最终DOCX文件并应用修订', defaultProgress: 95 },
  completed: { label: '处理完成', description: '文档已生成，可以下载', defaultProgress: 100 },
  failed: { label: '处理失败', description: '处理过程中出现错误', defaultProgress: 0 },
};

function getStages(taskStatus: TaskStatus | null) {
  const stages = ['parsing'];
  
  if (taskStatus?.enable_cleaning) {
    stages.push('cleaning');
  }
  if (taskStatus?.enable_correction) {
    stages.push('correcting');
  }
  
  stages.push('recognizing', 'formatting', 'generating');
  
  return stages;
}

export function Process() {
  const navigate = useNavigate();
  const { currentTaskId, taskStatus, setTaskStatus, reset } = useUploadStore();
  const [isLLM, setIsLLM] = useState(false);
  const [, setLlmChecked] = useState(false);
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalLines]);

  useEffect(() => {
    if (!currentTaskId) return;

    getTaskStatus(currentTaskId).then((status) => {
      setTaskStatus(status);
      if (status.enable_llm === 1) {
        setIsLLM(true);
      } else if (status.status === 'completed' || status.status === 'failed') {
        setLlmChecked(true);
      }
    }).catch(() => {
      setLlmChecked(true);
    });
  }, [currentTaskId, setTaskStatus]);

  useEffect(() => {
    if (!isLLM || !currentTaskId) return;

    setCurrentStage('connecting');

    const es = connectLLMStream(currentTaskId, {
      onProgress: (data: SSEProgressEvent) => {
        setCurrentStage(data.stage);
        setTerminalLines(prev => [...prev, `\x1b[36m▸ ${data.message}\x1b[0m`]);
      },
      onChunk: (data) => {
        setTerminalLines(prev => {
          const lastIdx = prev.length - 1;
          if (lastIdx >= 0 && !prev[lastIdx].startsWith('\x1b[36m')) {
            const updated = [...prev];
            updated[lastIdx] += data.content;
            return updated;
          }
          return [...prev, data.content];
        });
      },
      onAnalysis: (data: SSEAnalysisEvent) => {
        setAnalysisResult(JSON.stringify(data.structure, null, 2));
        setTerminalLines(prev => [
          ...prev,
          '\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m',
          `\x1b[32m✓ 识别完成 | 共 ${data.structure.paragraphs?.length || 0} 个段落 | 置信度 ${data.structure.overall_confidence}\x1b[0m`,
        ]);
      },
      onDone: (data: SSEDoneEvent) => {
        setLlmChecked(true);
        setTerminalLines(prev => [
          ...prev,
          `\x1b[32m✓ 处理完成 | 用时 ${data.processing_time}秒\x1b[0m`,
        ]);
        setCurrentStage('completed');
        if (currentTaskId) {
          getTaskStatus(currentTaskId).then(s => setTaskStatus(s)).catch(() => {});
        }
      },
      onError: (data: SSEErrorEvent) => {
        setTerminalLines(prev => [
          ...prev,
          `\x1b[31m✗ 错误: ${data.message}\x1b[0m`,
        ]);
        setLlmChecked(true);
        setCurrentStage('error');
        if (currentTaskId) {
          getTaskStatus(currentTaskId).then(s => setTaskStatus(s)).catch(() => {});
        }
      },
    });

    eventSourceRef.current = es;

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [isLLM, currentTaskId, setTaskStatus]);

  const handleStatusUpdate = useCallback((newStatus: TaskStatus) => {
    setTaskStatus(newStatus);
    if (newStatus.status === 'completed' || newStatus.status === 'failed') {
      setLlmChecked(true);
    }
  }, [setTaskStatus]);

  const handleComplete = useCallback((_status: TaskStatus) => {
    setLlmChecked(true);
  }, []);

  useTaskPolling({
    taskId: (!isLLM && currentTaskId) ? currentTaskId : null,
    interval: 2000,
    onSuccess: handleStatusUpdate,
    onComplete: handleComplete,
  });

  // 计算真实进度
  const progress = useMemo(() => {
    if (!taskStatus) return 0;
    if (taskStatus.status === 'completed') return 100;
    if (taskStatus.status === 'failed') return 0;
    // 如果有真实的 progress 字段，使用它
    if (taskStatus.progress > 0) return taskStatus.progress;
    // 否则使用阶段的默认进度
    const stage = taskStatus.processing_stage || 'parsing';
    return STAGE_CONFIG[stage]?.defaultProgress || 10;
  }, [taskStatus]);

  // 动态阶段列表
  const stages = useMemo(() => getStages(taskStatus), [taskStatus]);

  // 当前活跃的阶段索引
  const currentStageIndex = useMemo(() => {
    if (!taskStatus) return -1;
    if (taskStatus.status === 'completed') return stages.length;
    if (taskStatus.status === 'failed') return -1;
    const stage = taskStatus.processing_stage || 'parsing';
    return stages.indexOf(stage);
  }, [taskStatus, stages]);

  // 检查是否是临时任务ID（正在上传中）
  const isUploading = currentTaskId?.startsWith('temp-');

  if (!currentTaskId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <EmptyState
          title="没有正在进行的任务"
          action={{ label: '返回首页', onClick: () => navigate('/') }}
        />
      </div>
    );
  }

  const isCompleted = taskStatus?.status === 'completed';
  const isFailed = taskStatus?.status === 'failed';
  const isProcessing = isUploading || taskStatus?.status === 'processing' || taskStatus?.status === 'pending';

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className={isLLM ? 'max-w-4xl mx-auto px-4' : 'max-w-2xl mx-auto px-4'}>
        <div className="bg-white rounded-lg shadow-sm p-8">
          {/* 标题 */}
          <div className="text-center mb-6">
            {isCompleted ? (
              <>
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">处理完成！</h1>
              </>
            ) : isFailed ? (
              <>
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-red-600">处理失败</h1>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {isLLM ? 'AI 处理中...' : '处理中...'}
                </h1>
              </>
            )}
          </div>

          {/* 进度条 */}
          <div className="mb-6">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-1000 ${
                  isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-600'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between items-center mt-2">
              <p className="text-sm text-gray-500">
                {taskStatus?.processing_stage && STAGE_CONFIG[taskStatus.processing_stage]
                  ? `${STAGE_CONFIG[taskStatus.processing_stage].label} (${progress}%)`
                  : `${progress}%`
                }
              </p>
              {taskStatus?.processing_time && (
                <p className="text-sm text-gray-400">
                  用时 {taskStatus.processing_time.toFixed(1)} 秒
                </p>
              )}
            </div>
          </div>

          {/* LLM 终端面板 */}
          {isLLM && terminalLines.length > 0 && (
            <div className="mb-6">
              <div
                ref={terminalRef}
                className="bg-gray-900 rounded-lg p-4 h-80 overflow-y-auto font-mono text-sm"
              >
                {terminalLines.map((line, i) => (
                  <TerminalLine key={i} text={line} />
                ))}
                {!isCompleted && !isFailed && currentStage === 'recognizing' && (
                  <span className="inline-block w-2 h-4 bg-green-400 animate-pulse" />
                )}
              </div>

              {/* 分析结果查看按钮 */}
              {analysisResult && (
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowJson(!showJson)}
                    className="text-sm"
                  >
                    {showJson ? '隐藏 JSON 结果' : '查看完整 JSON 结果'}
                  </Button>
                </div>
              )}

              {/* JSON 结果面板 */}
              {showJson && analysisResult && (
                <div className="mt-3 bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <pre className="text-green-400 text-xs font-mono whitespace-pre-wrap">
                    {analysisResult}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 处理阶段详细列表 */}
          {isProcessing && (
            <div className="space-y-2 mb-8">
              {/* 上传阶段（仅在正在上传时显示） */}
              {isUploading && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-blue-700">
                      上传文件
                      <span className="ml-2 text-xs text-blue-500 animate-pulse">进行中...</span>
                    </div>
                    <div className="text-xs mt-0.5 text-blue-500">
                      正在将文件上传到服务器...
                    </div>
                  </div>
                </div>
              )}
              {stages.map((stageKey, index) => {
                const stage = STAGE_CONFIG[stageKey];
                const isActive = index === currentStageIndex;
                const isDone = index < currentStageIndex || isCompleted;

                return (
                  <div 
                    key={stageKey} 
                    className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
                      isActive ? 'bg-blue-50 border border-blue-200' : 
                      isDone ? 'bg-green-50' : 'bg-gray-50'
                    }`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {isDone ? (
                        <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      ) : isActive ? (
                        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${
                        isDone ? 'text-green-700' : isActive ? 'text-blue-700' : 'text-gray-400'
                      }`}>
                        {stage.label}
                        {isActive && <span className="ml-2 text-xs text-blue-500 animate-pulse">进行中...</span>}
                      </div>
                      <div className={`text-xs mt-0.5 ${
                        isDone ? 'text-green-600' : isActive ? 'text-blue-500' : 'text-gray-400'
                      }`}>
                        {stage.description}
                      </div>
                    </div>
                    {isDone && (
                      <span className="text-xs text-green-600 font-medium">完成</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* 任务信息 */}
          {taskStatus && (
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">任务信息</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <p>文件名：{taskStatus.input_filename}</p>
                <p>任务ID：{taskStatus.task_id}</p>
                {taskStatus.processing_time && (
                  <p>总用时：{taskStatus.processing_time.toFixed(1)} 秒</p>
                )}
              </div>
            </div>
          )}

          {/* PDF检测信息 */}
          {isCompleted && taskStatus?.pdf_info && (
            <PdfDetectionCard pdfInfo={taskStatus.pdf_info} />
          )}

          {/* 错误信息 */}
          {isFailed && taskStatus?.error_message && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <h3 className="text-sm font-medium text-red-800 mb-1">错误信息</h3>
              <p className="text-sm text-red-600">{taskStatus.error_message}</p>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-center space-x-4">
            {isCompleted ? (
              <>
                <Button
                  size="lg"
                  onClick={() => {
                    const a = document.createElement('a');
                    a.href = getDownloadUrl(currentTaskId);
                    a.download = taskStatus?.output_filename || 'formatted.docx';
                    a.click();
                  }}
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  下载文件
                </Button>
                <Button variant="outline" size="lg" onClick={() => navigate(`/preview/${currentTaskId}`)}>
                  查看解析预览
                </Button>
                <Button variant="outline" onClick={() => { reset(); navigate('/'); }}>
                  处理新文件
                </Button>
              </>
            ) : isFailed ? (
              <>
                <Button onClick={() => { reset(); navigate('/'); }}>
                  重新上传
                </Button>
                <Button variant="outline" onClick={() => navigate('/tasks')}>
                  查看任务列表
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={async () => {
                eventSourceRef.current?.close();
                if (currentTaskId) {
                  try { await cancelTask(currentTaskId); } catch {}
                }
                navigate('/');
              }}>
                取消并返回
              </Button>
            )}
          </div>

          {/* 完成后的说明和反馈 */}
          {isCompleted && (
            <>
              <div className="bg-blue-50 rounded-lg p-4 mt-6">
                <div className="flex items-start">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="text-sm text-blue-700">
                    <p className="font-medium">说明：</p>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>下载的文件包含Word原生修订和批注</li>
                      <li>您可以在Word中一键接受/驳回单条修订</li>
                      <li>批注内容为疑似问题，仅供参考</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200 text-center">
                <p className="text-sm text-gray-500 mb-2">对结果不满意？</p>
                <Button variant="outline" size="sm" onClick={() => navigate('/feedback')}>
                  提交反馈帮助我们改进
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function TerminalLine({ text }: { text: string }) {
  const parts: { content: string; color?: string }[] = [];
  let remaining = text;
  const colorMap: Record<string, string> = {
    '32': 'text-green-400',
    '31': 'text-red-400',
    '33': 'text-yellow-400',
    '36': 'text-cyan-400',
    '0': '',
  };

  const ansiRegex = /\x1b\[(\d+)m/g;
  let lastIndex = 0;
  let currentColor = '';
  let match;

  while ((match = ansiRegex.exec(remaining)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ content: remaining.slice(lastIndex, match.index), color: currentColor });
    }
    currentColor = colorMap[match[1]] || '';
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < remaining.length) {
    parts.push({ content: remaining.slice(lastIndex), color: currentColor });
  }

  if (parts.length === 0) {
    return <div className="text-gray-300 whitespace-pre-wrap">{text}</div>;
  }

  return (
    <div className="whitespace-pre-wrap">
      {parts.map((part, i) => (
        <span key={i} className={part.color || 'text-gray-300'}>
          {part.content}
        </span>
      ))}
    </div>
  );
}

const PDF_TYPE_CONFIG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  native: { color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', icon: 'text-green-500' },
  scanned: { color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-500' },
  mixed: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-500' },
};

function PdfDetectionCard({ pdfInfo }: { pdfInfo: PdfInfo }) {
  const cfg = PDF_TYPE_CONFIG[pdfInfo.type] || PDF_TYPE_CONFIG.native;
  const confidencePct = Math.round(pdfInfo.confidence * 100);

  return (
    <div className={`${cfg.bg} border ${cfg.border} rounded-lg p-4 mb-6`}>
      <div className="flex items-center gap-2 mb-3">
        <svg className={`w-5 h-5 ${cfg.icon}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 className={`text-sm font-medium ${cfg.color}`}>PDF 检测结果</h3>
      </div>
      <div className={`text-sm ${cfg.color} space-y-1.5`}>
        <div className="flex items-center gap-2">
          <span className="opacity-60 w-16 flex-shrink-0">类型</span>
          <span className="font-medium">{pdfInfo.type_name}</span>
          <span className="text-xs opacity-60">（置信度 {confidencePct}%）</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="opacity-60 w-16 flex-shrink-0">页数</span>
          <span>共 {pdfInfo.total_pages} 页</span>
          {pdfInfo.type === 'mixed' && (
            <span className="text-xs opacity-60">
              （原生 {pdfInfo.native_pages} 页 / 扫描 {pdfInfo.scanned_pages} 页）
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="opacity-60 w-16 flex-shrink-0">处理方式</span>
          <span>{pdfInfo.processing_hint}</span>
        </div>
      </div>
    </div>
  );
}
