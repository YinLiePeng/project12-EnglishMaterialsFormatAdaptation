import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadStore } from '../store/uploadStore';
import { useTaskPolling } from '../hooks/useTaskPolling';
import { connectLLMStream, getTaskStatus, getDownloadUrl, cancelTask } from '../services/api';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/EmptyState';
import type { TaskStatus, SSEProgressEvent, SSEAnalysisEvent, SSEDoneEvent, SSEErrorEvent } from '../types';

const STAGES = [
  { key: 'pending', label: '等待处理' },
  { key: 'processing', label: '解析文件' },
  { key: 'formatting', label: '格式化中' },
  { key: 'generating', label: '生成文档' },
  { key: 'completed', label: '处理完成' },
];

const STAGE_MESSAGES: Record<string, string> = {
  parsing: '解析文件中...',
  cleaning: '清洗内容中...',
  correcting: '纠错内容中...',
  recognizing: 'AI 结构识别中...',
  formatting: '排版生成中...',
};

export function Process() {
  const navigate = useNavigate();
  const { currentTaskId, taskStatus, setTaskStatus, reset } = useUploadStore();
  const [progress, setProgress] = useState(0);
  const [isLLM, setIsLLM] = useState(false);
  const [llmChecked, setLlmChecked] = useState(false);

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

    setProgress(10);
    setCurrentStage('connecting');

    const es = connectLLMStream(currentTaskId, {
      onProgress: (data: SSEProgressEvent) => {
        setCurrentStage(data.stage);
        setTerminalLines(prev => [...prev, `\x1b[36m▸ ${data.message}\x1b[0m`]);
        const stageProgress: Record<string, number> = {
          parsing: 15,
          cleaning: 25,
          correcting: 35,
          recognizing: 50,
          formatting: 85,
        };
        setProgress(stageProgress[data.stage] || 50);
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
        setProgress(100);
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

  const handleStatusUpdate = useCallback((status: TaskStatus) => {
    setTaskStatus(status);
    if (!isLLM && !llmChecked) {
      if (status.status === 'pending') setProgress(10);
      else if (status.status === 'processing') setProgress(50);
    }
  }, [setTaskStatus, isLLM, llmChecked]);

  const handleComplete = useCallback((status: TaskStatus) => {
    if (status.status === 'completed') {
      setProgress(100);
    } else {
      setProgress(0);
    }
    setLlmChecked(true);
  }, []);

  useTaskPolling({
    taskId: (!isLLM && currentTaskId) ? currentTaskId : null,
    interval: 2000,
    onSuccess: handleStatusUpdate,
    onComplete: handleComplete,
  });

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
  const isProcessing = taskStatus?.status === 'processing' || taskStatus?.status === 'pending';

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
                className={`h-full transition-all duration-500 ${
                  isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-600'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500 text-center mt-2">
              {isLLM && currentStage && STAGE_MESSAGES[currentStage]
                ? STAGE_MESSAGES[currentStage]
                : `${progress}%`}
            </p>
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

          {/* 非LLM模式的处理阶段 */}
          {!isLLM && isProcessing && (
            <div className="space-y-3 mb-8">
              {STAGES.map((stage, index) => {
                const stageProgress = (index + 1) * 20;
                const isActive = progress >= stageProgress - 10 && progress < stageProgress;
                const isDone = progress >= stageProgress;

                return (
                  <div key={stage.key} className="flex items-center">
                    {isDone ? (
                      <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    ) : isActive ? (
                      <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-3" />
                    ) : (
                      <div className="w-5 h-5 border-2 border-gray-300 rounded-full mr-3" />
                    )}
                    <span className={isDone ? 'text-green-600' : isActive ? 'text-blue-600' : 'text-gray-400'}>
                      {stage.label}
                    </span>
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
                  <p>处理用时：{taskStatus.processing_time}秒</p>
                )}
              </div>
            </div>
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
