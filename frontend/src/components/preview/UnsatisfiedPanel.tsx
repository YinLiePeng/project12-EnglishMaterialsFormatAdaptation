export interface UnsatisfiedPanelProps {
  onSelectDirect: () => void;
  onSelectAI: () => void;
  onCancel: () => void;
}

export function UnsatisfiedPanel({ onSelectDirect, onSelectAI, onCancel }: UnsatisfiedPanelProps) {
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
