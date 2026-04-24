import type { StyleConfig } from '../../types';
import { ALIGNMENT_LABEL } from '../../utils/styleMapping';

interface StyleParametersProps {
  style: StyleConfig;
}

export function StyleParameters({ style }: StyleParametersProps) {
  const parameters = [
    {
      label: '标题',
      value: `${style.heading1.font.name.split(' ')[0]} ${style.heading1.font.size}pt`,
      icon: '𝐇',
    },
    {
      label: '正文',
      value: `${style.body.font.name.split(' ')[0]} ${style.body.font.size}pt`,
      icon: '𝐓',
    },
    {
      label: '行距',
      value: `${style.body.format.line_spacing}倍`,
      icon: '↔',
    },
    {
      label: '对齐',
      value: ALIGNMENT_LABEL[style.body.format.alignment] || style.body.format.alignment,
      icon: '≣',
    },
  ];

  return (
    <div className="flex items-center justify-between">
      <h4 className="text-xs font-medium text-gray-700">样式参数</h4>
      <div className="flex space-x-3">
        {parameters.map((param) => (
          <div key={param.label} className="flex items-center space-x-1 text-xs text-gray-600">
            <span className="text-sm">{param.icon}</span>
            <span className="text-gray-500">{param.label}:</span>
            <span className="font-medium text-gray-900">{param.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
