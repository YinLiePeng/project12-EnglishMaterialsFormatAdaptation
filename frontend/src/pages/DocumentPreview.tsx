import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTaskStatus } from '../services/api';
import { Button } from '../components/common/Button';
import type { StructureAnalysis, TaskStatus } from '../types';

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

export function DocumentPreview() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [analysis, setAnalysis] = useState<StructureAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredParagraph, setHoveredParagraph] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

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

  // 获取置信度颜色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // 悬停左栏段落
  const handleParagraphHover = useCallback((index: number) => {
    setHoveredParagraph(index);

    // 滚动右栏到对应位置
    const rightItem = document.getElementById(`right-item-${index}`);
    if (rightItem && rightPanelRef.current) {
      rightItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  // 悬停右栏条目
  const handleRightItemHover = useCallback((index: number) => {
    setHoveredParagraph(index);

    // 滚动左栏到对应位置
    const leftItem = document.getElementById(`left-item-${index}`);
    if (leftItem && leftPanelRef.current) {
      leftItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  // 过滤段落
  const filteredParagraphs = analysis?.paragraphs.filter(p =>
    p.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.content_type_name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // 下载文件
  const handleDownload = () => {
    if (taskId) {
      window.open(`/api/v1/tasks/${taskId}/download`, '_blank');
    }
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
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => navigate(-1)}>
              ← 返回
            </Button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">📄 文档解析预览</h1>
              <p className="text-sm text-gray-500 truncate max-w-md">
                {taskStatus?.input_filename}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-1 rounded ${
              analysis.method === 'llm'
                ? 'bg-purple-100 text-purple-800'
                : 'bg-blue-100 text-blue-800'
            }`}>
              {analysis.method === 'llm' ? '🤖 大模型识别' : '⚙️ 规则引擎'}
            </span>
            <span className="text-sm text-gray-600">
              整体置信度: {(analysis.overall_confidence * 100).toFixed(0)}%
            </span>
            <Button onClick={handleDownload}>📥 下载文件</Button>
          </div>
        </div>
      </div>

      {/* 双栏内容 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6" style={{ height: 'calc(100vh - 120px)' }}>
          {/* 左栏：模拟文档预览 */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="bg-white rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b bg-gray-50">
                <h2 className="font-medium text-gray-700">📄 模拟文档预览</h2>
                <p className="text-xs text-gray-500 mt-1">悬停段落查看识别结果</p>
              </div>
              <div
                ref={leftPanelRef}
                className="flex-1 overflow-y-auto p-6"
              >
                <div className="bg-white border rounded-lg shadow-sm max-w-2xl mx-auto" style={{ minHeight: '800px' }}>
                  <div className="p-8 space-y-1">
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
          </div>

          {/* 右栏：结构识别结果 */}
          <div className="w-96 overflow-hidden flex flex-col">
            <div className="bg-white rounded-lg shadow-sm flex-1 overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b bg-gray-50">
                <h2 className="font-medium text-gray-700">🔍 结构识别结果</h2>
                <p className="text-xs text-gray-500 mt-1">共 {analysis.paragraphs.length} 个段落</p>
              </div>

              {/* 搜索框 */}
              <div className="px-4 py-3 border-b">
                <input
                  type="text"
                  placeholder="搜索段落或类型..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* 右栏列表 */}
              <div
                ref={rightPanelRef}
                className="flex-1 overflow-y-auto"
              >
                {filteredParagraphs.map((para) => {
                  const isHovered = hoveredParagraph === para.index;

                  return (
                    <div
                      key={para.index}
                      id={`right-item-${para.index}`}
                      className={`
                        border-b transition-all cursor-pointer
                        ${isHovered ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'}
                      `}
                      onMouseEnter={() => handleRightItemHover(para.index)}
                    >
                      <div className="px-4 py-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-gray-400 font-mono">#{para.index}</span>
                              <span className={`text-xs px-2 py-0.5 rounded border ${CONTENT_TYPE_COLORS[para.content_type] || CONTENT_TYPE_COLORS.body}`}>
                                {para.content_type_name}
                              </span>
                            </div>
                            <p className="text-sm text-gray-800 line-clamp-2">
                              {para.text}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <div className="w-14 bg-gray-200 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${getConfidenceColor(para.confidence)}`}
                                style={{ width: `${para.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-500">
                              {(para.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>

                        {/* 展开的详情 */}
                        {isHovered && (
                          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                            {/* 原始样式 */}
                            <div className="text-xs">
                              <span className="text-gray-500">原始样式:</span>
                              <span className="ml-1 text-gray-700">
                                {(para as any).original_style?.font_name || '宋体'}
                                {' '}
                                {(para as any).original_style?.font_size || 12}pt
                                {(para as any).original_style?.font_bold ? ' 加粗' : ''}
                                {' · '}
                                {(para as any).original_style?.alignment === 'center' ? '居中' :
                                 (para as any).original_style?.alignment === 'left' ? '左对齐' :
                                 (para as any).original_style?.alignment === 'right' ? '右对齐' : '两端对齐'}
                              </span>
                            </div>

                            {/* 将应用样式 */}
                            <div className="text-xs">
                              <span className="text-gray-500">将应用:</span>
                              <span className="ml-1 text-blue-700 font-medium">
                                {para.applied_style.name} · {para.applied_style.font.name}
                                {' '}{para.applied_style.font.size}pt
                                {para.applied_style.font.bold ? ' 加粗' : ''}
                              </span>
                            </div>

                            {/* 识别理由 */}
                            {para.reason && (
                              <div className="text-xs">
                                <span className="text-gray-500">理由:</span>
                                <span className="ml-1 text-gray-600">{para.reason}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
