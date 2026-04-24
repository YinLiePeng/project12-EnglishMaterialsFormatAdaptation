import { useState, useRef, useEffect } from 'react';

interface ModeOption {
  id: 'none' | 'empty' | 'complete';
  title: string;
  description: string;
  detail: string;
}

const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'none',
    title: '无模板排版',
    description: '使用系统预设的标准化样式，无需上传模板',
    detail: '系统内置多套面向全国卷中高考英语教学场景的预设排版样式（专题讲义、模拟试卷、作文范文等），选择后即可一键生成格式化文档，无需上传任何模板。适合没有固定校内模板要求的教师。',
  },
  {
    id: 'empty',
    title: '空模板排版',
    description: '上传单位空模板，需标记内容插入位置',
    detail: '适合学校要求使用统一模板的场景。上传学校提供的空白模板，选择预设排版样式，然后在模板正文区域标记一个填充位置，系统会自动将格式化后的内容填充到指定位置。',
  },
  {
    id: 'complete',
    title: '完整模板排版',
    description: '上传带格式模板，自动匹配并还原格式',
    detail: '上传一份已有内容和格式的样例文档，系统自动提取其全部格式参数（字体字号、行间距、缩进等），并将原始资料的内容按照相同的样式层级进行 1:1 格式还原。适合需要严格对齐某份样例格式的场景。',
  },
];

interface ModeSelectorProps {
  value: 'none' | 'empty' | 'complete';
  onChange: (mode: 'none' | 'empty' | 'complete') => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  const [popoverId, setPopoverId] = useState<string | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (popoverId === null) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setPopoverId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [popoverId]);

  return (
    <div className="flex gap-2 flex-wrap">
      {MODE_OPTIONS.map((option) => {
        const isSelected = value === option.id;
        const isPopoverOpen = popoverId === option.id;

        return (
          <button
            key={option.id}
            onClick={() => onChange(option.id)}
            title={option.description}
            className={`relative px-4 py-1.5 rounded-lg border-2 cursor-pointer transition-all text-left ${
              isSelected
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-1.5">
              <span className={`text-sm font-medium ${isSelected ? 'text-blue-700' : 'text-gray-700'}`}>
                {option.title}
              </span>
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation();
                  setPopoverId(isPopoverOpen ? null : option.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.stopPropagation();
                    setPopoverId(isPopoverOpen ? null : option.id);
                  }
                }}
                className={`w-4 h-4 rounded-full inline-flex items-center justify-center flex-shrink-0 transition-colors ${
                  isPopoverOpen
                    ? 'bg-blue-100 text-blue-600'
                    : 'text-gray-300 hover:text-blue-500'
                }`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </span>
            </div>
            <span className="block text-xs text-gray-400 line-clamp-1">{option.description}</span>

            {isPopoverOpen && (
              <div
                ref={popoverRef}
                className="absolute top-full left-0 mt-2 w-72 p-3 bg-white rounded-lg shadow-lg border border-gray-100 text-xs text-gray-600 leading-relaxed z-50"
              >
                {option.detail}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
