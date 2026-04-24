import { useState, useEffect, useRef } from 'react';
import { CONTENT_TYPE_COLORS, CONTENT_TYPE_OPTIONS, formatStyleSummary } from '../../constants/contentTypes';
import type { ParagraphEdit } from '../../types';

export interface TypeSelectorProps {
  paraIndex: number;
  currentType: string;
  edits: ParagraphEdit[];
  typeStyleMap: Record<string, any>;
  hasEdit: boolean;
  onSelect: (index: number, type: string) => void;
  onRevert: (index: number) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export function TypeSelector({ paraIndex, currentType, edits, typeStyleMap, hasEdit, onSelect, onRevert, containerRef }: TypeSelectorProps) {
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
