import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTaskStatus, quickCorrection, aiRecognize, regenerateDocument } from '../services/api';
import { Button } from '../components/common/Button';
import { CorrectionPreviewModal } from '../components/CorrectionPreviewModal';
import { useToast } from '../contexts/ToastContext';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { CONTENT_TYPE_HIGHLIGHT, CONTENT_TYPE_NAMES, formatStyleSummary } from '../constants/contentTypes';
import { mapFontName, mapLineSpacing, indentToEm, ptToPx } from '../utils/styleMapping';
import type { StructureAnalysis, TaskStatus, ParagraphEdit, CorrectionChange } from '../types';
import { UnsatisfiedPanel } from '../components/preview/UnsatisfiedPanel';
import { AIFeedbackModal } from '../components/preview/AIFeedbackModal';
import { TypeSelector } from '../components/preview/TypeSelector';

function buildTypeStyleMap(paragraphs: any[]): Record<string, any> {
  const map: Record<string, any> = {};
  for (const p of paragraphs) {
    const ct = p.content_type;
    if (!map[ct] && p.applied_style) {
      map[ct] = p.applied_style;
    }
  }
  return map;
}

export function DocumentPreview() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [exitConfirmOpen, setExitConfirmOpen] = useState(false);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [analysis, setAnalysis] = useState<StructureAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredParagraph, setHoveredParagraph] = useState<number | null>(null);

  const [showChoicePanel, setShowChoicePanel] = useState(false);
  const [correctionMode, setCorrectionMode] = useState<null | 'direct' | 'ai'>(null);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewChanges, setPreviewChanges] = useState<CorrectionChange[]>([]);
  const [edits, setEdits] = useState<ParagraphEdit[]>([]);
  const [showTypeSelector, setShowTypeSelector] = useState<number | null>(null);

  const [showAIModal, setShowAIModal] = useState(false);
  const [aiFeedback, setAiFeedback] = useState('');
  const [mobileTab, setMobileTab] = useState<'left' | 'right'>('left');

  const leftPanelRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);

  const isEditMode = correctionMode !== null;

  const typeStyleMap = analysis?.style_map && Object.keys(analysis.style_map).length > 0
    ? analysis.style_map
    : (analysis ? buildTypeStyleMap(analysis.paragraphs) : {});

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

  useEffect(() => {
    const leftPanel = leftPanelRef.current;
    const rightPanel = rightPanelRef.current;

    if (!leftPanel || !rightPanel || !analysis) return;

    let isScrolling = false;
    let scrollTimeout: number | null = null;

    const handleLeftScroll = () => {
      if (isScrolling) return;
      isScrolling = true;

      const leftScrollableHeight = leftPanel.scrollHeight - leftPanel.clientHeight;
      const rightScrollableHeight = rightPanel.scrollHeight - rightPanel.clientHeight;

      if (leftScrollableHeight > 0 && rightScrollableHeight > 0) {
        const scrollRatio = leftPanel.scrollTop / leftScrollableHeight;
        rightPanel.scrollTop = scrollRatio * rightScrollableHeight;
      }

      if (scrollTimeout) clearTimeout(scrollTimeout);
      scrollTimeout = window.setTimeout(() => { isScrolling = false; }, 150);
    };

    const handleRightScroll = () => {
      if (isScrolling) return;
      isScrolling = true;

      const leftScrollableHeight = leftPanel.scrollHeight - leftPanel.clientHeight;
      const rightScrollableHeight = rightPanel.scrollHeight - rightPanel.clientHeight;

      if (leftScrollableHeight > 0 && rightScrollableHeight > 0) {
        const scrollRatio = rightPanel.scrollTop / rightScrollableHeight;
        leftPanel.scrollTop = scrollRatio * leftScrollableHeight;
      }

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

  const handleParagraphHover = useCallback((index: number) => {
    setHoveredParagraph(index);
  }, []);

  const handleRightParagraphHover = useCallback((index: number) => {
    setHoveredParagraph(index);
  }, []);

  const handleDownload = () => {
    if (taskId) {
      window.open(`/api/v1/tasks/${taskId}/download`, '_blank');
    }
  };

  const handleExitEditMode = () => {
    if (edits.length > 0) {
      setExitConfirmOpen(true);
      return;
    }
    setCorrectionMode(null);
    setEdits([]);
    setShowTypeSelector(null);
    setShowAIModal(false);
    setAiFeedback('');
    setShowChoicePanel(false);
  };

  const handleExitConfirm = () => {
    setExitConfirmOpen(false);
    setCorrectionMode(null);
    setEdits([]);
    setShowTypeSelector(null);
    setShowAIModal(false);
    setAiFeedback('');
    setShowChoicePanel(false);
  };

  const handleUnsatisfied = () => {
    if (taskStatus?.preset_style === 'preserve') {
      showToast('此模式下不支持修改。如有需要，下载文档后自行修改更为便捷哦~', 'info');
      return;
    }
    setShowChoicePanel(true);
  };

  const handleSelectDirect = () => {
    setCorrectionMode('direct');
    setShowChoicePanel(false);
    setEdits([]);
    setShowTypeSelector(null);
  };

  const handleSelectAI = () => {
    setCorrectionMode('ai');
    setShowChoicePanel(false);
    setEdits([]);
    setShowTypeSelector(null);
  };

  const handleDirectComplete = async () => {
    if (edits.length === 0) {
      setCorrectionMode(null);
      return;
    }

    try {
      const response = await quickCorrection(taskId!, {
        paragraph_updates: edits.map(e => ({
          index: e.paragraphIndex,
          content_type: e.newType
        })),
      });

      if (response.updated_count > 0) {
        setAnalysis(response.structure_analysis);
        setEdits([]);
        setCorrectionMode(null);
        await handleRegenerate();
      }
    } catch (error) {
      console.error('快速修正失败:', error);
      showToast('修正失败，请重试', 'error');
    }
  };

  const handleSubmitToAI = () => {
    setShowAIModal(true);
    setAiFeedback('');
  };

  const [previewStructure, setPreviewStructure] = useState<StructureAnalysis | null>(null);

  const handleAIConfirm = async () => {
    setShowAIModal(false);
    setIsRecognizing(true);

    try {
      const previewResponse = await aiRecognize(taskId!, {
        user_feedback: aiFeedback,
        paragraph_updates: edits.map(e => ({
          index: e.paragraphIndex,
          content_type: e.newType,
        })),
        mode: 'preview'
      }) as any;

      const changes = previewResponse.changes || [];
      if (changes.length === 0) {
        showToast('AI 认为当前识别结果已经准确，无需修改。', 'info');
        return;
      }

      setPreviewChanges(changes);
      setPreviewStructure(previewResponse.structure_analysis);
      setShowPreviewModal(true);
    } catch (error) {
      console.error('AI识别失败:', error);
      showToast('AI识别失败，请重试', 'error');
    } finally {
      setIsRecognizing(false);
    }
  };

  const handleConfirmPreview = async () => {
    if (!previewStructure) return;

    try {
      const applyResponse = await aiRecognize(taskId!, {
        structure_analysis: previewStructure,
        mode: 'apply'
      }) as any;

      setAnalysis(previewStructure);
      setShowPreviewModal(false);
      setEdits([]);
      setCorrectionMode(null);
      setPreviewStructure(null);
      await handleRegenerate();
    } catch (error) {
      console.error('应用修正失败:', error);
      showToast('应用失败，请重试', 'error');
    }
  };

  const handleRegenerate = async () => {
    try {
      await regenerateDocument(taskId!);
      showToast('文档已重新生成，请下载新版本', 'success');
    } catch (error) {
      console.error('重新生成失败:', error);
      showToast('重新生成失败', 'error');
    }
  };

  const handleTypeChange = (paragraphIndex: number, newType: string) => {
    const para = analysis?.paragraphs[paragraphIndex];
    if (!para) return;

    const existingEdit = edits.find(e => e.paragraphIndex === paragraphIndex);

    if (existingEdit) {
      setEdits(edits.map(e =>
        e.paragraphIndex === paragraphIndex
          ? { ...e, newType }
          : e
      ));
    } else {
      setEdits([...edits, {
        paragraphIndex,
        originalType: para.content_type,
        newType
      }]);
    }

    setShowTypeSelector(null);
  };

  const handleRevert = (paragraphIndex: number) => {
    setEdits(edits.filter(e => e.paragraphIndex !== paragraphIndex));
    setShowTypeSelector(null);
  };

  const getEditSummary = () => {
    return edits.map(e => {
      const para = analysis?.paragraphs[e.paragraphIndex];
      const text = para?.text?.slice(0, 30) || '';
      return {
        index: e.paragraphIndex,
        oldType: CONTENT_TYPE_NAMES[e.originalType] || e.originalType,
        newType: CONTENT_TYPE_NAMES[e.newType] || e.newType,
        text,
      };
    });
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
              <h1 className="text-base font-semibold text-gray-900">文档解析预览</h1>
              <p className="text-xs text-gray-500 truncate max-w-md">
                {taskStatus?.input_filename}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* 初始状态：显示"不满意"按钮 */}
            {!isEditMode && !showChoicePanel && (
              <Button variant="outline" onClick={handleUnsatisfied}>
                😕 不满意
              </Button>
            )}

            {/* 直接修改模式 */}
            {correctionMode === 'direct' && (
              <>
                <span className="text-sm text-gray-600">✏️ 直接修改</span>
                {edits.length > 0 && (
                  <>
                    <span className="text-xs text-amber-600">
                      已修改 {edits.length} 处
                    </span>
                    <Button variant="outline" onClick={() => { setEdits([]); setShowTypeSelector(null); }}>
                      ↩️ 重置全部
                    </Button>
                    <Button onClick={handleDirectComplete}>
                      ✓ 完成 ({edits.length})
                    </Button>
                  </>
                )}
              </>
            )}

            {/* AI辅助修改模式 */}
            {correctionMode === 'ai' && (
              <>
                <span className="text-sm text-gray-600">🤖 AI辅助修改</span>
                {edits.length > 0 && (
                  <>
                    <span className="text-xs text-amber-600">
                      已修改 {edits.length} 处
                    </span>
                    <Button variant="outline" onClick={() => { setEdits([]); setShowTypeSelector(null); }}>
                      ↩️ 重置全部
                    </Button>
                  </>
                )}
                <Button
                  onClick={handleSubmitToAI}
                  disabled={isRecognizing}
                >
                  {isRecognizing ? 'AI 处理中（约需1-2分钟）...' : `📋 提交给AI${edits.length > 0 ? ` (${edits.length})` : ''}`}
                </Button>
              </>
            )}

            {/* 编辑模式下的取消按钮 */}
            {isEditMode && (
              <Button variant="outline" onClick={handleExitEditMode}>
                ✕ 取消
              </Button>
            )}

            <Button onClick={handleDownload}>📥 下载</Button>
          </div>
        </div>

        {/* 编辑模式下的提示 */}
        {isEditMode && (
          <div className="max-w-screen-2xl mx-auto px-2 py-1 border-t bg-amber-50">
            <div className="flex items-center gap-3">
              <div className="text-xs text-gray-600 flex gap-2">
                <span>💡 点击右栏段落可修改类型</span>
                {correctionMode === 'ai' && (
                  <span>💡 修改后点击"提交给AI"，AI将参考您的调整进行全局优化</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* "不满意"选择面板 */}
      {showChoicePanel && !isEditMode && (
        <UnsatisfiedPanel
          onSelectDirect={handleSelectDirect}
          onSelectAI={handleSelectAI}
          onCancel={() => setShowChoicePanel(false)}
        />
      )}

      {/* 双栏内容 */}
      <div className={`max-w-screen-2xl mx-auto px-2 py-3 ${!isEditMode && !showChoicePanel ? 'pt-0' : ''}`}>
        {/* 移动端Tab切换 */}
        <div className="flex lg:hidden mb-2 bg-white rounded-lg shadow-sm overflow-hidden">
          <button
            onClick={() => setMobileTab('left')}
            className={`flex-1 py-2 text-sm font-medium text-center transition-colors ${mobileTab === 'left' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-500'}`}
          >
            原文档
          </button>
          <button
            onClick={() => setMobileTab('right')}
            className={`flex-1 py-2 text-sm font-medium text-center transition-colors ${mobileTab === 'right' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-500'}`}
          >
            处理后
          </button>
        </div>

        <div className="flex gap-4" style={{ height: isEditMode ? 'calc(100vh - 140px)' : showChoicePanel ? 'calc(100vh - 250px)' : 'calc(100vh - 120px)' }}>
          {/* 左栏：原文档预览 */}
          <div className={`flex-1 overflow-hidden flex flex-col ${mobileTab !== 'left' ? 'hidden lg:flex' : ''}`}>
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
                    const originalStyle = para.original_style || {};

                    const leftStyle: React.CSSProperties = {
                      fontFamily: mapFontName(originalStyle.font_name),
                      fontSize: ptToPx(originalStyle.font_size || 12),
                      fontWeight: originalStyle.font_bold ? 'bold' : 'normal',
                      fontStyle: originalStyle.font_italic ? 'italic' : 'normal',
                      textDecoration: originalStyle.font_underline ? 'underline' : 'none',
                      color: originalStyle.font_color ? `#${originalStyle.font_color}` : undefined,
                      textAlign: (originalStyle.alignment as React.CSSProperties['textAlign']) || 'left',
                      lineHeight: originalStyle.line_spacing || 1.5,
                      marginTop: originalStyle.space_before ? ptToPx(originalStyle.space_before) : undefined,
                      marginBottom: originalStyle.space_after ? ptToPx(originalStyle.space_after) : undefined,
                      textIndent: originalStyle.first_line_indent ? indentToEm(originalStyle.first_line_indent) : undefined,
                      paddingLeft: originalStyle.left_indent ? ptToPx(originalStyle.left_indent) : undefined,
                    };

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
                        style={leftStyle}
                      >
                        <p>
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
          <div className={`flex-1 overflow-hidden flex flex-col ${mobileTab !== 'right' ? 'hidden lg:flex' : ''}`}>
            <div className="bg-white rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
              <div className="px-3 py-2 border-b bg-gray-50">
                <h2 className="text-sm font-medium text-gray-700">
                  ✨ 处理后文档
                  {isEditMode && '（点击段落修改类型）'}
                </h2>
                <p className="text-xs text-gray-500">
                  {isEditMode ? '点击段落修改类型' : '应用新样式'}
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

                    const paragraphStyle: React.CSSProperties = {
                      fontFamily: mapFontName(appliedStyle?.font?.name),
                      fontSize: ptToPx(appliedStyle?.font?.size || 12),
                      fontWeight: appliedStyle?.font?.bold ? 'bold' : 'normal',
                      fontStyle: appliedStyle?.font?.italic ? 'italic' : 'normal',
                      textDecoration: appliedStyle?.font?.underline ? 'underline' : 'none',
                      color: appliedStyle?.font?.color ? `#${appliedStyle.font.color}` : undefined,
                      textAlign: (appliedStyle?.format?.alignment as React.CSSProperties['textAlign']) || 'left',
                      lineHeight: mapLineSpacing(
                        appliedStyle?.format?.line_spacing,
                        appliedStyle?.format?.line_spacing_rule,
                      ),
                      marginTop: appliedStyle?.format?.space_before ? ptToPx(appliedStyle.format.space_before) : undefined,
                      marginBottom: appliedStyle?.format?.space_after ? ptToPx(appliedStyle.format.space_after) : undefined,
                      textIndent: appliedStyle?.format?.first_line_indent ? indentToEm(appliedStyle.format.first_line_indent) : undefined,
                      paddingLeft: appliedStyle?.format?.left_indent ? ptToPx(appliedStyle.format.left_indent) : undefined,
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
                          <TypeSelector
                            paraIndex={para.index}
                            currentType={para.content_type}
                            edits={edits}
                            typeStyleMap={typeStyleMap}
                            hasEdit={hasEdit}
                            onSelect={handleTypeChange}
                            onRevert={handleRevert}
                            containerRef={rightPanelRef}
                          />
                        )}

                        {/* 悬停样式信息tooltip */}
                        {isHovered && !(isEditMode && showTypeSelector === para.index) && (
                          <div className="absolute -top-10 left-0 z-10 bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap max-w-[90vw]">
                            <span>
                              <strong>{para.content_type_name}</strong>
                              {' · '}
                              {formatStyleSummary(appliedStyle)}
                            </span>
                            {hasEdit && (
                              <span className="text-amber-400 ml-2">✏️ 已编辑</span>
                            )}
                          </div>
                        )}

                        {/* 编辑模式下的编辑标记 */}
                        {isEditMode && hasEdit && (
                          <div className="absolute -top-2 -right-2 bg-amber-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
                            ✏️
                          </div>
                        )}

                        <p>
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

      {/* AI 反馈模态框 */}
      {showAIModal && (
        <AIFeedbackModal
          editSummary={getEditSummary()}
          feedback={aiFeedback}
          onFeedbackChange={setAiFeedback}
          onConfirm={handleAIConfirm}
          onCancel={() => setShowAIModal(false)}
        />
      )}

      {/* 预览对话框 */}
      {showPreviewModal && (
        <CorrectionPreviewModal
          changes={previewChanges}
          onConfirm={handleConfirmPreview}
          onCancel={() => setShowPreviewModal(false)}
        />
      )}

      {/* 退出编辑确认 */}
      {exitConfirmOpen && (
        <ConfirmDialog
          title="退出编辑"
          message={`您有 ${edits.length} 处未保存的修改，确定要退出吗？`}
          confirmVariant="danger"
          confirmText="确认退出"
          onConfirm={handleExitConfirm}
          onCancel={() => setExitConfirmOpen(false)}
        />
      )}
    </div>
  );
}
