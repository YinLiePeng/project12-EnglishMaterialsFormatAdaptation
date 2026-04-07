interface ModeOption {
  id: 'none' | 'empty' | 'complete';
  title: string;
  description: string;
}

const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'none',
    title: '无模板排版',
    description: '使用系统预设的标准化样式，无需上传模板',
  },
  {
    id: 'empty',
    title: '空模板排版',
    description: '上传单位空模板，需标记内容插入位置',
  },
  {
    id: 'complete',
    title: '完整模板排版',
    description: '上传带格式模板，自动匹配并还原格式',
  },
];

interface ModeSelectorProps {
  value: 'none' | 'empty' | 'complete';
  onChange: (mode: 'none' | 'empty' | 'complete') => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {MODE_OPTIONS.map((option) => (
        <div
          key={option.id}
          onClick={() => onChange(option.id)}
          className={`
            p-6 rounded-lg border-2 cursor-pointer transition-all
            ${
              value === option.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }
          `}
        >
          <div className="flex items-start">
            <div
              className={`
                w-5 h-5 rounded-full border-2 mr-3 mt-0.5 flex items-center justify-center
                ${value === option.id ? 'border-blue-500' : 'border-gray-300'}
              `}
            >
              {value === option.id && (
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              )}
            </div>
            <div>
              <h3 className="font-medium text-gray-900">{option.title}</h3>
              <p className="text-sm text-gray-500 mt-1">{option.description}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
