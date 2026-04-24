import { Button } from './common/Button';
import type { CorrectionChange } from '../types';

interface CorrectionPreviewModalProps {
  changes: CorrectionChange[];
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 修正预览对话框 - 显示AI识别的变化列表
 */
export function CorrectionPreviewModal({
  changes,
  onConfirm,
  onCancel,
}: CorrectionPreviewModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="px-6 py-4 border-b bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>🤖</span>
            <span>确认AI识别修正</span>
          </h2>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <p className="text-sm text-gray-700 mb-4">
            AI识别将修改以下 <span className="font-semibold text-blue-600">{changes.length}</span> 个段落：
          </p>

          <div className="space-y-3">
            {changes.map((change) => (
              <div
                key={change.index}
                className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-gray-500">#{change.index}</span>
                      <span className="text-sm font-medium text-gray-900">
                        {change.old_type_name} → {change.new_type_name}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      💡 {change.reason}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 警告提示 */}
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-800 flex items-start gap-2">
              <span>⚠️</span>
              <span>提示：修改后的文档将替换当前版本，请确认后继续</span>
            </p>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={onConfirm}>
            确认并重新生成文档
          </Button>
        </div>
      </div>
    </div>
  );
}
