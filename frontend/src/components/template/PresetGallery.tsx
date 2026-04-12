import type { PresetStyle } from '../../types';

interface PresetGalleryProps {
  presets: PresetStyle[];
  value: string;
  onChange: (style: string) => void;
  onPreview: (styleId: string) => void;
}

const STYLE_GROUPS = [
  {
    title: '特殊 / 通用',
    styleIds: ['preserve', 'universal'],
  },
  {
    title: '按学段',
    styleIds: ['primary_low', 'primary_high', 'junior', 'senior'],
  },
  {
    title: '按用途',
    styleIds: ['exam', 'lecture', 'essay'],
  },
];

export function PresetGallery({ presets, value, onChange, onPreview }: PresetGalleryProps) {
  const presetMap = new Map(presets.map((p) => [p.id, p]));

  return (
    <div className="space-y-3">
      {STYLE_GROUPS.map((group) => (
        <div key={group.title}>
          <span className="text-xs text-gray-400 mb-1.5 block">{group.title}</span>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {group.styleIds.map((styleId) => {
              const preset = presetMap.get(styleId);
              if (!preset) return null;

              const isPreserve = styleId === 'preserve';
              const isSelected = value === preset.id;

              return (
                <div
                  key={preset.id}
                  onClick={() => onChange(preset.id)}
                  title={preset.description}
                  className={`p-2.5 rounded-lg border-2 cursor-pointer transition-all group ${
                    isSelected
                      ? isPreserve
                        ? 'border-green-500 bg-green-50'
                        : 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <div
                        className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                          isSelected
                            ? isPreserve ? 'border-green-500' : 'border-blue-500'
                            : 'border-gray-300'
                        }`}
                      >
                        {isSelected && (
                          <div className={`w-1.5 h-1.5 rounded-full ${isPreserve ? 'bg-green-500' : 'bg-blue-500'}`} />
                        )}
                      </div>
                      <span className="text-sm font-medium text-gray-900 truncate">{preset.name}</span>
                    </div>
                    {!isPreserve && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onPreview(preset.id);
                        }}
                        className="text-gray-300 hover:text-blue-500 transition-colors flex-shrink-0"
                        title="查看预览"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{preset.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
