import { useState } from 'react';
import type { StructureAnalysis } from '../types';

interface StructureAnalysisPanelProps {
  analysis: StructureAnalysis | null;
  loading?: boolean;
}

const CONTENT_TYPE_COLORS: Record<string, string> = {
  title: 'bg-purple-100 text-purple-800 border-purple-300',
  heading: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  question_number: 'bg-blue-100 text-blue-800 border-blue-300',
  option: 'bg-green-100 text-green-800 border-green-300',
  body: 'bg-gray-100 text-gray-800 border-gray-300',
  answer: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  analysis: 'bg-orange-100 text-orange-800 border-orange-300',
};

const CONTENT_TYPE_ICONS: Record<string, string> = {
  title: '📌',
  heading: '📝',
  question_number: '🔢',
  option: '☑️',
  body: '📄',
  answer: '✅',
  analysis: '💡',
};

export function StructureAnalysisPanel({ analysis, loading }: StructureAnalysisPanelProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6 text-center text-gray-500">
        <p>等待结构识别完成...</p>
      </div>
    );
  }

  const toggleExpand = (index: number) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedItems(newExpanded);
  };

  const filteredParagraphs = analysis.paragraphs.filter(p =>
    p.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.content_type_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      {/* 头部：方法和置信度 */}
      <div className="mb-6 pb-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">
            文章结构分析
          </h3>
          <span className={`text-xs px-2 py-1 rounded ${
            analysis.method === 'llm'
              ? 'bg-purple-100 text-purple-800'
              : 'bg-blue-100 text-blue-800'
          }`}>
            {analysis.method === 'llm' ? '🤖 大模型识别' : '⚙️ 规则引擎'}
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>整体置信度:</span>
          <div className="flex-1 max-w-xs bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getConfidenceColor(analysis.overall_confidence)}`}
              style={{ width: `${analysis.overall_confidence * 100}%` }}
            />
          </div>
          <span className="font-medium">{(analysis.overall_confidence * 100).toFixed(0)}%</span>
        </div>
        {analysis.summary && (
          <p className="text-sm text-gray-500 mt-2">{analysis.summary}</p>
        )}
      </div>

      {/* 搜索框 */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="搜索段落文本或类型..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* 段落列表 */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredParagraphs.length === 0 ? (
          <p className="text-center text-gray-500 py-8">没有匹配的段落</p>
        ) : (
          filteredParagraphs.map((para) => (
            <div
              key={para.index}
              className={`border rounded-lg transition-all ${
                expandedItems.has(para.index)
                  ? 'border-gray-300 bg-gray-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {/* 段落头部 */}
              <div
                className="p-3 cursor-pointer"
                onClick={() => toggleExpand(para.index)}
              >
                <div className="flex items-start gap-3">
                  {/* 序号 */}
                  <span className="text-xs text-gray-400 font-mono mt-1">
                    #{para.index}
                  </span>

                  {/* 文本预览 */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 line-clamp-1">
                      {para.text}
                    </p>
                  </div>

                  {/* 置信度 */}
                  <div className="flex flex-col items-end gap-1">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${getConfidenceColor(para.confidence)}`}
                        style={{ width: `${para.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">
                      {(para.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* 展开图标 */}
                  <span className="text-gray-400">
                    {expandedItems.has(para.index) ? '▼' : '▶'}
                  </span>
                </div>

                {/* 类型标签 */}
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-xs px-2 py-1 rounded border ${CONTENT_TYPE_COLORS[para.content_type] || CONTENT_TYPE_COLORS.body}`}
                  >
                    {CONTENT_TYPE_ICONS[para.content_type] || '📄'} {para.content_type_name}
                  </span>
                  {para.reason && (
                    <span className="text-xs text-gray-500">
                      {para.reason}
                    </span>
                  )}
                </div>
              </div>

              {/* 详细信息（可展开） */}
              {expandedItems.has(para.index) && (
                <div className="px-3 pb-3 border-t border-gray-100 pt-3">
                  {/* 将应用的样式 */}
                  <div className="bg-gray-50 rounded p-3">
                    <div className="text-xs font-medium text-gray-700 mb-2">
                      🎨 将应用的样式：{para.applied_style.name}
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      {/* 字体信息 */}
                      <div>
                        <span className="text-gray-500">字体:</span>
                        <span className="ml-1 font-medium text-gray-800">
                          {para.applied_style.font.name} {para.applied_style.font.size}pt
                          {para.applied_style.font.bold && ' 加粗'}
                        </span>
                      </div>

                      {/* 格式信息 */}
                      <div>
                        <span className="text-gray-500">对齐:</span>
                        <span className="ml-1 font-medium text-gray-800">
                          {para.applied_style.format.alignment === 'center' ? '居中' :
                           para.applied_style.format.alignment === 'left' ? '左对齐' :
                           para.applied_style.format.alignment === 'right' ? '右对齐' :
                           para.applied_style.format.alignment === 'justify' ? '两端对齐' :
                           para.applied_style.format.alignment}
                        </span>
                      </div>

                      <div>
                        <span className="text-gray-500">行距:</span>
                        <span className="ml-1 font-medium text-gray-800">
                          {para.applied_style.format.line_spacing}倍
                        </span>
                      </div>

                      {para.applied_style.format.first_line_indent !== undefined && (
                        <div>
                          <span className="text-gray-500">首行缩进:</span>
                          <span className="ml-1 font-medium text-gray-800">
                            {para.applied_style.format.first_line_indent}字符
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* 统计信息 */}
      <div className="mt-4 pt-3 border-t text-xs text-gray-500">
        共 {analysis.paragraphs.length} 个段落
        {searchQuery && `，显示 ${filteredParagraphs.length} 个匹配`}
      </div>
    </div>
  );
}
