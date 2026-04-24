import { useRef, useCallback, useMemo, useEffect } from 'react';
import type { MarkerPosition, TemplatePreviewResponse } from '../../types';

interface TemplatePreviewProps {
  preview: TemplatePreviewResponse;
  markerPosition: MarkerPosition | null;
  onMarkerSelect: (pos: MarkerPosition) => void;
}

export default function TemplatePreview({
  preview,
  markerPosition,
  onMarkerSelect,
}: TemplatePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      const target = (e.target as HTMLElement).closest(
        '[data-element-index]'
      ) as HTMLElement | null;
      if (!target) return;

      const elementIndex = Number(target.getAttribute('data-element-index'));
      const elementType = target.getAttribute('data-element-type');
      const row = target.getAttribute('data-row');
      const col = target.getAttribute('data-col');

      if ((elementType === 'table' || elementType === 'table_cell') && row !== null && col !== null) {
        onMarkerSelect({
          element_index: elementIndex,
          type: 'table_cell',
          table_index: 0,
          row: Number(row),
          col: Number(col),
        });
      } else if (elementType === 'paragraph' || elementType === 'blank_line') {
        onMarkerSelect({
          element_index: elementIndex,
          type: elementType === 'blank_line' ? 'blank_line_group' : 'paragraph',
        });
      }
    },
    [onMarkerSelect]
  );

  const markerLabel = useMemo(() => {
    if (!markerPosition) return '';
    if (markerPosition.type === 'table_cell') {
      const el = preview.elements.find(
        (e) => e.index === markerPosition.element_index
      );
      const rowSummary = el?.row_summaries?.find(
        (r) => r.row === markerPosition.row
      );
      const text = rowSummary?.text_preview || '';
      return `表格第${(markerPosition.row ?? 0) + 1}行` +
        (text ? ` (${text.slice(0, 20)})` : '');
    }
    if (markerPosition.type === 'paragraph') {
      const el = preview.elements.find(
        (e) => e.index === markerPosition.element_index
      );
      return `段落: ${(el?.text_preview || '').slice(0, 30)}`;
    }
    return '空白区域';
  }, [markerPosition, preview.elements]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    container.querySelectorAll('.marker-selected').forEach((el) => {
      el.classList.remove('marker-selected');
    });

    if (!markerPosition) return;

    if (markerPosition.type === 'table_cell') {
      const { row, col } = markerPosition;
      const cell = container.querySelector(
        `td[data-row="${row}"][data-col="${col}"]`
      );
      if (cell) cell.classList.add('marker-selected');
    } else if (markerPosition.type === 'paragraph') {
      const para = container.querySelector(
        `p[data-element-index="${markerPosition.element_index}"][data-element-type="paragraph"]`
      );
      if (para) para.classList.add('marker-selected');
    } else if (markerPosition.type === 'blank_line_group') {
      const el = container.querySelector(
        `p[data-element-index="${markerPosition.element_index}"][data-element-type="blank_line"]`
      );
      if (el) el.classList.add('marker-selected');
    }
  }, [markerPosition, preview.html]);

  useEffect(() => {
    if (!containerRef.current) return;
    const cells = containerRef.current.querySelectorAll(
      'td[data-row][data-col]'
    );
    cells.forEach((cell) => {
      (cell as HTMLElement).style.cursor = 'pointer';
    });
    const paras = containerRef.current.querySelectorAll(
      'p[data-element-type="paragraph"], p[data-element-type="blank_line"]'
    );
    paras.forEach((p) => {
      (p as HTMLElement).style.cursor = 'pointer';
    });
  }, [preview.html]);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-blue-50 border-b border-blue-100 px-3 py-2 flex items-center justify-between">
        <div className="text-sm font-medium text-blue-800">
          模板预览 — 点击选择内容填充位置
        </div>
        <div className="text-xs text-blue-600">
          {preview.filename}
        </div>
      </div>

      <div className="p-4 bg-white max-h-[500px] overflow-y-auto">
        {preview.auto_detected_area && !markerPosition && (
          <div className="mb-3 p-2.5 bg-green-50 border border-green-200 rounded-md flex items-start gap-2">
            <svg className="w-4 h-4 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <div className="text-sm text-green-800 font-medium">
                系统检测到疑似内容区域
              </div>
              <div className="text-xs text-green-700 mt-0.5">
                {preview.auto_detected_area.reason}
              </div>
              <button
                className="mt-1.5 text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 transition-colors"
                onClick={() => {
                  const area = preview.auto_detected_area!;
                  onMarkerSelect({
                    element_index: area.element_index,
                    type: area.type as MarkerPosition['type'],
                    table_index: area.table_index,
                    row: area.row,
                    col: area.col,
                  });
                }}
              >
                使用此位置
              </button>
              <span className="text-xs text-green-600 ml-2">或点击下方预览手动选择</span>
            </div>
          </div>
        )}

        {markerPosition && (
          <div className="mb-3 p-2.5 bg-blue-50 border border-blue-200 rounded-md flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-blue-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <div className="text-sm text-blue-800 font-medium">
                  已选择填充位置
                </div>
                <div className="text-xs text-blue-600">{markerLabel}</div>
              </div>
            </div>
            <button
              className="text-xs text-red-600 hover:text-red-800 underline"
              onClick={() => onMarkerSelect(null as unknown as MarkerPosition)}
            >
              重新选择
            </button>
          </div>
        )}

        <div
          ref={containerRef}
          className="template-preview-content"
          onClick={handleClick}
          dangerouslySetInnerHTML={{ __html: preview.html }}
          style={{
            fontFamily: '宋体, SimSun, serif',
            fontSize: '12pt',
            lineHeight: '1.5',
            color: '#333',
          }}
        />
      </div>

      <style>{`
        .template-preview-content .doc-table {
          border-collapse: collapse;
          width: 100%;
          margin: 8px 0;
        }
        .template-preview-content .doc-table td {
          border: 1px solid #d0d0d0;
          padding: 6px 8px;
          transition: background-color 0.15s, outline 0.15s;
          position: relative;
        }
        .template-preview-content .doc-table td:hover {
          background-color: rgba(59, 130, 246, 0.08) !important;
          outline: 2px solid #3b82f6;
          outline-offset: -2px;
        }
        .template-preview-content .doc-table td.marker-selected {
          background-color: rgba(34, 197, 94, 0.12) !important;
          outline: 3px solid #22c55e !important;
          outline-offset: -3px;
        }
        .template-preview-content .doc-para:hover {
          background-color: rgba(59, 130, 246, 0.06);
          outline: 1px dashed #93c5fd;
          outline-offset: 2px;
          border-radius: 2px;
        }
        .template-preview-content .doc-para.marker-selected {
          background-color: rgba(34, 197, 94, 0.12) !important;
          outline: 3px solid #22c55e !important;
          outline-offset: 2px;
          border-radius: 2px;
        }
        .template-preview-content .doc-blank:hover {
          background-color: rgba(59, 130, 246, 0.06);
          outline: 1px dashed #93c5fd;
          outline-offset: 2px;
          border-radius: 2px;
        }
        .template-preview-content .doc-blank.marker-selected {
          background-color: rgba(34, 197, 94, 0.12) !important;
          outline: 3px solid #22c55e !important;
          outline-offset: 2px;
          border-radius: 2px;
        }
        .template-preview-content .doc-image {
          margin: 8px 0;
          text-align: center;
        }
        .template-preview-content .doc-image img {
          max-width: 100%;
          height: auto;
        }
      `}</style>
    </div>
  );
}
