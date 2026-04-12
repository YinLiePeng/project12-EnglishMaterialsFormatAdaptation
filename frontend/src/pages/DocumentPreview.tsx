import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTaskStatus, quickCorrection, aiRecognize, regenerateDocument } from '../services/api';
import { Button } from '../components/common/Button';
import { CorrectionPreviewModal } from '../components/CorrectionPreviewModal';
import { mapFontName, mapLineSpacing, indentToEm, ptToPx } from '../utils/styleMapping';
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

const CONTENT_TYPE_OPTIONS = [
  { value: 'title', label: '主标题' },
  { value: 'heading', label: '子标题' },
  { value: 'question_number', label: '题号' },
  { value: 'option', label: '选项' },
  { value: 'body', label: '正文' },
  { value: 'answer', label: '答案' },
  { value: 'analysis', label: '解析' },
];

const CONTENT_TYPE_NAMES: Record<string, string> = {
  title: '主标题',
  heading: '子标题',
  question_number: '题号',
  option: '选项',
  body: '正文',
  answer: '答案',
  analysis: '解析',
};

const ALIGNMENT_LABELS: Record<string, string> = {
  left: '左对齐',
  center: '居中',
  right: '右对齐',
  justify: '两端对齐',
};

function formatStyleSummary(style: any): string {
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
      const ok = window.confirm(`您有 ${edits.length} 处未保存的修改，确定要退出吗？`);
      if (!ok) return;
    }
    setCorrectionMode(null);
    setEdits([]);
    setShowTypeSelector(null);
    setShowAIModal(false);
    setAiFeedback('');
    setShowChoicePanel(false);
  };

  const handleUnsatisfied = () => {
    if (taskStatus?.preset_style === 'preserve') {
      alert('此模式下不支持修改。如有需要，下载文档后自行修改更为便捷哦~');
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
      alert('修正失败，请重试');
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
        alert('AI 认为当前识别结果已经准确，无需修改。');
        return;
      }

      setPreviewChanges(changes);
      setPreviewStructure(previewResponse.structure_analysis);
      setShowPreviewModal(true);
    } catch (error) {
      console.error('AI识别失败:', error);
      alert('AI识别失败，请重试');
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
      alert('应用失败，请重试');
    }
  };

  const handleRegenerate = async () => {
    try {
      await regenerateDocument(taskId!);
      alert('文档已重新生成，请下载新版本');
    } catch (error) {
      console.error('重新生成失败:', error);
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
              <h1 className="text-base font-semibold text-gray-900">📄 文档解析预览</h1>
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
        <div className="flex gap-4" style={{ height: isEditMode ? 'calc(100vh - 140px)' : showChoicePanel ? 'calc(100vh - 250px)' : 'calc(100vh - 120px)' }}>
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
          <div className="flex-1 overflow-hidden flex flex-col">
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
    </div>
  );
}

function UnsatisfiedPanel({ onSelectDirect, onSelectAI, onCancel }: {
  onSelectDirect: () => void;
  onSelectAI: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="bg-white border-b">
      <div className="max-w-screen-2xl mx-auto px-2 py-4 relative">
        <button
          onClick={onCancel}
          className="absolute top-3 right-4 text-gray-400 hover:text-gray-600 text-lg"
        >
          ✕
        </button>
        <p className="text-sm text-gray-600 mb-3 text-center">
          请选择修改方式：
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={onSelectDirect}
            className="flex flex-col items-center gap-2 px-8 py-4 rounded-lg border-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-all cursor-pointer group"
          >
            <span className="text-2xl">✏️</span>
            <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700">直接修改</span>
            <span className="text-xs text-gray-400">手动调整段落类型，立即生效</span>
          </button>
          <button
            onClick={onSelectAI}
            className="flex flex-col items-center gap-2 px-8 py-4 rounded-lg border-2 border-gray-200 hover:border-purple-400 hover:bg-purple-50 transition-all cursor-pointer group"
          >
            <span className="text-2xl">🤖</span>
            <span className="text-sm font-medium text-gray-700 group-hover:text-purple-700">AI辅助修改</span>
            <span className="text-xs text-gray-400">先调整部分段落作为示例，AI参考后全局优化</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function AIFeedbackModal({ editSummary, feedback, onFeedbackChange, onConfirm, onCancel }: {
  editSummary: { index: number; oldType: string; newType: string; text: string }[];
  feedback: string;
  onFeedbackChange: (v: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">🤖 AI 辅助修正</h3>
          <p className="text-sm text-gray-500 mt-1">AI将参考您的调整示例进行全局优化</p>
        </div>

        <div className="px-6 py-4 space-y-4">
          {editSummary.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">您的调整示例：</h4>
              <div className="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                {editSummary.map(e => (
                  <div key={e.index} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400 font-mono">#{e.index}</span>
                    <span className="text-gray-600">{e.text ? `${e.text}...` : ''}</span>
                    <span className="text-gray-400">→</span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700">
                      {e.oldType}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700">
                      {e.newType}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              补充说明（可选）
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="例如：前面数字开头的都应该识别为题号，而不是正文"
              value={feedback}
              onChange={(e) => onFeedbackChange(e.target.value)}
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t flex items-center justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>取消</Button>
          <Button onClick={onConfirm}>确认并交给AI</Button>
        </div>
      </div>
    </div>
  );
}

function TypeSelector({ paraIndex, currentType, edits, typeStyleMap, hasEdit, onSelect, onRevert, containerRef }: {
  paraIndex: number;
  currentType: string;
  edits: ParagraphEdit[];
  typeStyleMap: Record<string, any>;
  hasEdit: boolean;
  onSelect: (index: number, type: string) => void;
  onRevert: (index: number) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
}) {
  const selectorRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<'top' | 'bottom'>('top');

  useEffect(() => {
    const el = selectorRef.current;
    const container = containerRef.current;
    if (!el || !container) return;

    const elRect = el.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    if (elRect.top < containerRect.top) {
      setPosition('bottom');
    }
  }, []);

  return (
    <div
      ref={selectorRef}
      className={`absolute left-0 z-20 bg-white rounded-lg shadow-lg border p-2 min-w-[320px] ${
        position === 'top' ? '-top-1 translate-y-[-100%]' : 'top-full mt-1'
      }`}
    >
      <div className="text-[10px] text-gray-500 mb-1">选择段落类型：</div>
      <div className="grid grid-cols-2 gap-1">
        {CONTENT_TYPE_OPTIONS.map(option => {
          const effectiveType = edits.find(e => e.paragraphIndex === paraIndex)?.newType || currentType;
          const isSelected = effectiveType === option.value;
          const styleSummary = typeStyleMap[option.value]
            ? formatStyleSummary(typeStyleMap[option.value])
            : '';
          return (
            <button
              key={option.value}
              className={`text-left text-xs px-2 py-1 rounded border cursor-pointer hover:ring-2 transition-all ${
                isSelected
                  ? `${CONTENT_TYPE_COLORS[option.value]} ring-2 ring-blue-400`
                  : `${CONTENT_TYPE_COLORS[option.value]}`
              }`}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(paraIndex, option.value);
              }}
            >
              <span className="font-medium">{option.label}</span>
              {styleSummary && (
                <span className="block text-[10px] opacity-60 truncate leading-tight">{styleSummary}</span>
              )}
            </button>
          );
        })}
      </div>
      {hasEdit && (
        <button
          className="w-full text-xs bg-gray-100 text-gray-700 rounded px-2 py-1 mt-1 hover:bg-gray-200 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onRevert(paraIndex);
          }}
        >
          ↩️ 恢复原始类型
        </button>
      )}
    </div>
  );
}
