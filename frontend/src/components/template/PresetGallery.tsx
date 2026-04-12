import { useState } from 'react';
import type { PresetStyle } from '../../types';
import { StylePreviewDrawer } from './StylePreviewDrawer';

interface PresetGalleryProps {
  presets: PresetStyle[];
  value: string;
  onChange: (style: string) => void;
}

const STYLE_GROUPS = [
  {
    title: '特殊方案',
    description: '按原样保留文档格式',
    styleIds: ['preserve'],
  },
  {
    title: '通用方案',
    description: '适用于各类场景',
    styleIds: ['universal'],
  },
  {
    title: '按学段分类',
    description: '根据年级选择',
    styleIds: ['primary_low', 'primary_high', 'junior', 'senior'],
  },
  {
    title: '按用途分类',
    description: '根据资料类型选择',
    styleIds: ['exam', 'lecture', 'essay'],
  },
];

export function PresetGallery({ presets, value, onChange }: PresetGalleryProps) {
  const presetMap = new Map(presets.map((p) => [p.id, p]));
  const [previewStyleId, setPreviewStyleId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {STYLE_GROUPS.map((group) => (
        <div key={group.title}>
          <div className="mb-3">
            <h3 className="text-sm font-medium text-gray-900">{group.title}</h3>
            <p className="text-xs text-gray-500">{group.description}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {group.styleIds.map((styleId) => {
              const preset = presetMap.get(styleId);
              if (!preset) return null;

              const isPreserve = styleId === 'preserve';

              return (
                <div
                  key={preset.id}
                  onClick={() => onChange(preset.id)}
                  className={`
                    p-4 rounded-lg border-2 cursor-pointer transition-all
                    ${
                      value === preset.id
                        ? isPreserve
                          ? 'border-green-500 bg-green-50 shadow-sm'
                          : 'border-blue-500 bg-blue-50 shadow-sm'
                        : isPreserve
                        ? 'border-green-200 hover:border-green-300 hover:bg-green-50/50'
                        : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                    }
                  `}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start flex-1 min-w-0">
                      <div
                        className={`
                          w-4 h-4 rounded-full border-2 mr-2 mt-0.5 flex-shrink-0 flex items-center justify-center
                          ${value === preset.id
                            ? isPreserve ? 'border-green-500' : 'border-blue-500'
                            : 'border-gray-300'}
                        `}
                      >
                        {value === preset.id && (
                          <div className={`w-2 h-2 rounded-full ${isPreserve ? 'bg-green-500' : 'bg-blue-500'}`} />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          {isPreserve && (
                            <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                          )}
                          <h4 className="font-medium text-gray-900 text-sm truncate">
                            {preset.name}
                          </h4>
                        </div>
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                          {preset.description}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewStyleId(preset.id);
                      }}
                      className={`ml-2 transition-colors flex-shrink-0 p-1 ${
                        isPreserve ? 'text-green-400 hover:text-green-600' : 'text-gray-400 hover:text-blue-600'
                      }`}
                      title="查看详情"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <StylePreviewDrawer
        isOpen={previewStyleId !== null}
        onClose={() => setPreviewStyleId(null)}
        styleId={previewStyleId || ''}
        styles={presets}
        onApply={(styleId) => {
          onChange(styleId);
          setPreviewStyleId(null);
        }}
      />
    </div>
  );
}
