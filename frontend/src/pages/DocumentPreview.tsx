import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTaskStatus, quickCorrection, aiRecognize, regenerateDocument } from '../services/api';
import { Button } from '../components/common/Button';
import { CorrectionPreviewModal } from '../components/CorrectionPreviewModal';
import type { StructureAnalysis, TaskStatus, ParagraphEdit, CorrectionChange } from '../types';

const CONTENT_TYPE_COLORS: Record<string, string> = {
  title: 'bg-purple-100 text-purple-800 border-purple-300',
  heading: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  question_number: 'bg-blue-100 text-blue-800 border-blue-300',
  option: 'bg-green-100 text-green-800 border-green-300',
  body: 'bg-gray-100 text-gray-800 border-gray-300',
  answer: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  analysis: 'bg-orange-100 text-orange-800 border-orange-300',
};

const CONTENT_TYPE_HIGHLIGHT: Record<string, string> = {
  title: 'ring-2 ring-purple-400 bg-purple-50',
  heading: 'ring-2 ring-indigo-400 bg-indigo-50',
  question_number: 'ring-2 ring-blue-400 bg-blue-50',
  option: 'ring-2 ring-green-400 bg-green-50',
  body: 'ring-2 ring-gray-400 bg-gray-50',
  answer: 'ring-2 ring-yellow-400 bg-yellow-50',
  analysis: 'ring-2 ring-orange-400 bg-orange-50',
};

const ALIGNMENT_MAP: Record<string, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
  justify: 'text-justify',
};

const CONTENT_TYPE_OPTIONS = [
  { value: 'title', label: '主标题' },
  { value: 'heading', label: '子标题' },
  { value: 'question_number', label: '题号' },
  { value: 'option', label: '选项' },
  { value: 'body', label: '正文' },
  { value: 'answer', label: '答案' },
  { value: 'analysis', label: '解析' },
];

export function DocumentPreview() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [analysis, setAnalysis] = useState<StructureAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredParagraph, setHoveredParagraph] = useState<number | null>(null);

  // 编辑模式状态
  const [isEditMode, setIsEditMode] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewChanges, setPreviewChanges] = useState<CorrectionChange[]>([]);
  const [edits, setEdits] = useState<ParagraphEdit[]>([]);
  const [showTypeSelector, setShowTypeSelector] = useState<number | null>(null);

  const leftPanelRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);

  // 加载任务数据
  useEffect(() => {
    const fetchTask = async () => {
      if (!taskId) return;

      try {
        const data = await getTaskStatus(taskId);
        setTaskStatus(data);
        if (data.structure_analysis) {
          setAnalysis(data.structure_analysis);
        }
      } catch (error) {
        console.error('加载任务数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTask();
  }, [taskId]);

  // 同步滚动
  useEffect(() => {
    const leftPanel = leftPanelRef.current;
    const rightPanel = rightPanelRef.current;

    if (!leftPanel || !rightPanel || !analysis) return;

    let isScrolling = false;
    let scrollTimeout: number | null = null;

    const handleLeftScroll = () => {
      if (isScrolling) return;
      isScrolling = true;

      // 防止除以0
      const leftScrollableHeight = leftPanel.scrollHeight - leftPanel.clientHeight;
      const rightScrollableHeight = rightPanel.scrollHeight - rightPanel.clientHeight;
      
      if (leftScrollableHeight > 0 && rightScrollableHeight > 0) {
        const scrollRatio = leftPanel.scrollTop / leftScrollableHeight;
        rightPanel.scrollTop = scrollRatio * rightScrollableHeight;
      }

      // 清除之前的timeout
      if (scrollTimeout) clearTimeout(scrollTimeout);
      scrollTimeout = window.setTimeout(() => { isScrolling = false; }, 150);
    };

    const handleRightScroll = () => {
      if (isScrolling) return;
      isScrolling = true;

      // 防止除以0
      const leftScrollableHeight = leftPanel.scrollHeight - leftPanel.clientHeight;
      const rightScrollableHeight = rightPanel.scrollHeight - rightPanel.clientHeight;
      
      if (leftScrollableHeight > 0 && rightScrollableHeight > 0) {
        const scrollRatio = rightPanel.scrollTop / rightScrollableHeight;
        leftPanel.scrollTop = scrollRatio * leftScrollableHeight;
      }

      // 清除之前的timeout
      if (scrollTimeout) clearTimeout(scrollTimeout);
      scrollTimeout = window.setTimeout(() => { isScrolling = false; }, 150);
    };

    leftPanel.addEventListener('scroll', handleLeftScroll, { passive: true });
    rightPanel.addEventListener('scroll', handleRightScroll, { passive: true });

    return () => {
      leftPanel.removeEventListener('scroll', handleLeftScroll);
      rightPanel.removeEventListener('scroll', handleRightScroll);
      if (scrollTimeout) clearTimeout(scrollTimeout);
    };
  }, [analysis]);

  // 悬停左栏段落
  const handleParagraphHover = useCallback((index: number) => {
    setHoveredParagraph(index);
  }, []);

  // 悬停右栏段落
  const handleRightParagraphHover = useCallback((index: number) => {
    setHoveredParagraph(index);
    // 移除自动滚动功能，避免事件循环导致连续滚动
    // 只保留悬停高亮功能，配合同步滚动使用
  }, []);

  // 下载文件
  const handleDownload = () => {
    if (taskId) {
      window.open(`/api/v1/tasks/${taskId}/download`, '_blank');
    }
  };

  // 切换编辑模式
  const handleToggleEditMode = () => {
    if (isEditMode && edits.length > 0) {
      const confirm = window.confirm(`您有 ${edits.length} 处未保存的修改，确定要退出编辑模式吗？`);
      if (!confirm) return;
      setEdits([]);
    }
    setIsEditMode(!isEditMode);
    setShowTypeSelector(null);
  };

  // 快速修正：更新段落类型
  const handleQuickCorrection = async () => {
    if (edits.length === 0) return;

    try {
      const response = await quickCorrection(taskId!, {
        paragraph_updates: edits.map(e => ({
          index: e.paragraphIndex,
          content_type: e.newType
        })),
        user_feedback: feedback
      });

      if (response.updated_count > 0) {
        setAnalysis(response.structure_analysis);
        setEdits([]);

        // 自动重新生成文档
        await handleRegenerate();
      }
    } catch (error) {
      console.error('快速修正失败:', error);
      alert('修正失败，请重试');
    }
  };

  // AI识别
  const handleAIRecognize = async () => {
    setIsRecognizing(true);

    try {
      // 第一步：预览模式
      const previewResponse = await aiRecognize(taskId!, {
        user_feedback: feedback,
        mode: 'preview'
      }) as any;

      if (previewResponse.changes) {
        setShowPreviewModal(true);
        setPreviewChanges(previewResponse.changes);
      }
    } catch (error) {
      console.error('AI识别失败:', error);
      alert('AI识别失败，请重试');
    } finally {
      setIsRecognizing(false);
    }
  };

  // 确认预览并应用
  const handleConfirmPreview = async () => {
    try {
      // 第二步：应用模式
      const applyResponse = await aiRecognize(taskId!, {
        user_feedback: feedback,
        mode: 'apply'
      }) as any;

      if (applyResponse.applied_count > 0) {
        setAnalysis(applyResponse.structure_analysis);
        setShowPreviewModal(false);
        setEdits([]);

        // 自动重新生成文档
        await handleRegenerate();
      }
    } catch (error) {
      console.error('应用修正失败:', error);
      alert('应用失败，请重试');
    }
  };

  // 重新生成文档
  const handleRegenerate = async () => {
    try {
      await regenerateDocument(taskId!);
      alert('文档已重新生成，请下载新版本');
    } catch (error) {
      console.error('重新生成失败:', error);
    }
  };

  // 处理段落类型变更
  const handleTypeChange = (paragraphIndex: number, newType: string) => {
    const para = analysis?.paragraphs[paragraphIndex];
    if (!para) return;

    const existingEdit = edits.find(e => e.paragraphIndex === paragraphIndex);

    if (existingEdit) {
      // 更新现有编辑
      setEdits(edits.map(e =>
        e.paragraphIndex === paragraphIndex
          ? { ...e, newType }
          : e
      ));
    } else {
      // 添加新编辑
      setEdits([...edits, {
        paragraphIndex,
        originalType: para.content_type,
        newType
      }]);
    }

    setShowTypeSelector(null);
  };

  // 恢复编辑
  const handleRevert = (paragraphIndex: number) => {
    setEdits(edits.filter(e => e.paragraphIndex !== paragraphIndex));
    setShowTypeSelector(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">该任务没有结构分析数据</p>
          <Button onClick={() => navigate(-1)}>返回</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-screen-2xl mx-auto px-2 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => navigate(-1)}>
              ← 返回
            </Button>
            <div>
              <h1 className="text-base font-semibold text-gray-900">📄 文档解析预览</h1>
              <p className="text-xs text-gray-500 truncate max-w-md">
                {taskStatus?.input_filename}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* 编辑模式按钮 */}
            <Button
              variant={isEditMode ? "primary" : "outline"}
              onClick={handleToggleEditMode}
            >
              {isEditMode ? '✓ 完成' : '😕 不满意'}
            </Button>

            {/* 编辑模式下的操作按钮 */}
            {isEditMode && (
              <>
                {edits.length > 0 && (
                  <span className="text-xs text-amber-600">
                    已编辑 {edits.length} 处
                  </span>
                )}
                {edits.length > 0 && (
                  <Button onClick={handleQuickCorrection}>
                    💾 保存 ({edits.length})
                  </Button>
                )}
                <Button
                  onClick={handleAIRecognize}
                  disabled={isRecognizing}
                >
                  {isRecognizing ? '🤖 识别中' : '🤖 AI'}
                </Button>
              </>
            )}

            <Button onClick={handleDownload}>📥 下载</Button>
          </div>
        </div>

        {/* 编辑模式下的反馈面板 */}
        {isEditMode && (
          <div className="max-w-screen-2xl mx-auto px-2 py-1 border-t bg-amber-50">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <textarea
                  className="w-full px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={1}
                  placeholder="说明问题（可选）例如：段落3应该是标题"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
              </div>
              <div className="text-xs text-gray-600 flex gap-2">
                <span>💡 点击段落修改</span>
                <span>💡 💾保存立即生效</span>
                <span>💡 🤖AI智能优化</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 双栏内容 */}
      <div className="max-w-screen-2xl mx-auto px-2 py-3">
        <div className="flex gap-4" style={{ height: 'calc(100vh - 140px)' }}>
          {/* 左栏：原文档预览 */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="bg-white rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
              <div className="px-3 py-2 border-b bg-gray-50">
                <h2 className="text-sm font-medium text-gray-700">📄 原文档（处理前）</h2>
                <p className="text-xs text-gray-500">应用原始样式</p>
              </div>
              <div
                ref={leftPanelRef}
                className="flex-1 overflow-y-auto p-4"
              >
                <div className="bg-white border rounded-lg shadow-sm max-w-3xl mx-auto p-6" style={{ minHeight: '800px' }}>
                  {analysis.paragraphs.map((para) => {
                    const isHovered = hoveredParagraph === para.index;
                    const originalStyle = (para as any).original_style || {};

                    return (
                      <div
                        key={para.index}
                        id={`left-item-${para.index}`}
                        className={`
                          p-2 rounded cursor-pointer transition-all
                          ${isHovered
                            ? `${CONTENT_TYPE_HIGHLIGHT[para.content_type]} ring-offset-2`
                            : 'hover:bg-gray-50'
                          }
                        `}
                        onMouseEnter={() => handleParagraphHover(para.index)}
                        style={{
                          fontFamily: originalStyle.font_name || '宋体',
                          fontSize: `${Math.min(originalStyle.font_size || 12, 18)}px`,
                          fontWeight: originalStyle.font_bold ? 'bold' : 'normal',
                        }}
                      >
                        <p className={`${ALIGNMENT_MAP[originalStyle.alignment || 'left']} leading-relaxed`}>
                          {para.text || <span className="text-gray-300">(空行)</span>}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* 右栏：处理后文档预览 */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="bg-white rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
              <div className="px-3 py-2 border-b bg-gray-50">
                <h2 className="text-sm font-medium text-gray-700">
                  ✨ 处理后文档
                  {isEditMode && '（编辑）'}
                </h2>
                <p className="text-xs text-gray-500">
                  {isEditMode ? '点击段落修改' : '应用新样式'}
                </p>
              </div>

              <div
                ref={rightPanelRef}
                className="flex-1 overflow-y-auto p-4"
              >
                <div className="bg-white border rounded-lg shadow-sm max-w-3xl mx-auto p-6 relative" style={{ minHeight: '800px' }}>
                  {analysis.paragraphs.map((para) => {
                    const isHovered = hoveredParagraph === para.index;
                    const hasEdit = edits.some(e => e.paragraphIndex === para.index);
                    const appliedStyle = para.applied_style;

                    // 计算段落样式
                    const paragraphStyle: React.CSSProperties = {
                      fontFamily: appliedStyle?.font?.name || '宋体',
                      fontSize: `${appliedStyle?.font?.size || 12}pt`,
                      fontWeight: appliedStyle?.font?.bold ? 'bold' : 'normal',
                      textAlign: appliedStyle?.format?.alignment as any || 'left',
                      lineHeight: appliedStyle?.format?.line_spacing || 1.5,
                      marginBottom: `${appliedStyle?.format?.space_after || 0}pt`,
                      textIndent: `${appliedStyle?.format?.first_line_indent || 0}pt`,
                    };

                    return (
                      <div
                        key={para.index}
                        id={`right-item-${para.index}`}
                        className={`
                          relative group p-2 rounded transition-all
                          ${isHovered ? 'bg-blue-50' : ''}
                          ${hasEdit ? 'ring-2 ring-amber-400' : ''}
                          ${isEditMode ? 'cursor-pointer hover:ring-2 hover:ring-blue-300' : ''}
                        `}
                        onMouseEnter={() => handleRightParagraphHover(para.index)}
                        onClick={() => {
                          if (isEditMode) {
                            setShowTypeSelector(showTypeSelector === para.index ? null : para.index);
                          }
                        }}
                        style={paragraphStyle}
                      >
                        {/* 编辑模式下的类型选择器 */}
                        {isEditMode && showTypeSelector === para.index && (
                          <div className="absolute -top-16 left-0 z-10 bg-white rounded-lg shadow-lg border p-3 space-y-2">
                            <div className="text-xs text-gray-600 mb-1">选择段落类型：</div>
                            <div className="grid grid-cols-4 gap-1">
                              {CONTENT_TYPE_OPTIONS.map(option => (
                                <button
                                  key={option.value}
                                  className={`text-xs px-2 py-1 rounded border cursor-pointer hover:ring-2 transition-all ${
                                    (edits.find(e => e.paragraphIndex === para.index)?.newType || para.content_type) === option.value
                                      ? `${CONTENT_TYPE_COLORS[option.value]} ring-2 ring-blue-400`
                                      : `${CONTENT_TYPE_COLORS[option.value]}`
                                  }`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleTypeChange(para.index, option.value);
                                  }}
                                >
                                  {option.label}
                                </button>
                              ))}
                            </div>
                            {hasEdit && (
                              <button
                                className="w-full text-xs bg-gray-100 text-gray-700 rounded px-2 py-1 hover:bg-gray-200 transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRevert(para.index);
                                }}
                              >
                                ↩️ 恢复原始类型
                              </button>
                            )}
                          </div>
                        )}

                        {/* 悬停样式信息tooltip */}
                        {isHovered && (
                          <div className="absolute -top-12 left-0 z-10 bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                            <div>
                              <strong>{para.content_type_name}</strong>
                              {' · '}
                              {appliedStyle?.font?.size}pt
                              {appliedStyle?.font?.bold ? ' 加粗' : ''}
                            </div>
                            <div className="text-gray-300">
                              {appliedStyle?.name}
                            </div>
                            {hasEdit && (
                              <div className="text-amber-400 mt-1">
                                ✏️ 已编辑
                              </div>
                            )}
                          </div>
                        )}

                        {/* 编辑模式下的编辑标记 */}
                        {isEditMode && hasEdit && (
                          <div className="absolute -top-2 -right-2 bg-amber-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
                            ✏️
                          </div>
                        )}

                        <p className="leading-relaxed">
                          {para.text || <span className="text-gray-300">(空行)</span>}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 预览对话框 */}
      {showPreviewModal && (
        <CorrectionPreviewModal
          changes={previewChanges}
          onConfirm={handleConfirmPreview}
          onCancel={() => setShowPreviewModal(false)}
        />
      )}
    </div>
  );
}
