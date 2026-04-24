import { Button } from '../common/Button';

export interface EditSummaryItem {
  index: number;
  oldType: string;
  newType: string;
  text: string;
}

export interface AIFeedbackModalProps {
  editSummary: EditSummaryItem[];
  feedback: string;
  onFeedbackChange: (v: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export function AIFeedbackModal({ editSummary, feedback, onFeedbackChange, onConfirm, onCancel }: AIFeedbackModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">🤖 AI 辅助修正</h3>
          <p className="text-sm text-gray-500 mt-1">AI将参考您的调整示例进行全局优化</p>
        </div>

        <div className="px-6 py-4 space-y-4">
          {editSummary.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">您的调整示例：</h4>
              <div className="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                {editSummary.map(e => (
                  <div key={e.index} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400 font-mono">#{e.index}</span>
                    <span className="text-gray-600">{e.text ? `${e.text}...` : ''}</span>
                    <span className="text-gray-400">→</span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700">
                      {e.oldType}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700">
                      {e.newType}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              补充说明（可选）
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="例如：前面数字开头的都应该识别为题号，而不是正文"
              value={feedback}
              onChange={(e) => onFeedbackChange(e.target.value)}
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t flex items-center justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>取消</Button>
          <Button onClick={onConfirm}>确认并交给AI</Button>
        </div>
      </div>
    </div>
  );
}
