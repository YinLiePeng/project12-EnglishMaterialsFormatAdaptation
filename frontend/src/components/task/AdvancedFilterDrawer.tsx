import { useState, useEffect } from 'react';
import { useTaskStore } from '../../store/taskStore';
import type { TaskFilters } from '../../types';

interface AdvancedFilterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '等待处理' },
  { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '处理失败' },
];

const LAYOUT_MODE_OPTIONS = [
  { value: '', label: '全部模式' },
  { value: 'none', label: '无模板排版' },
  { value: 'empty', label: '空模板排版' },
  { value: 'complete', label: '完整模板排版' },
];

const DATE_PRESETS = [
  { label: '今天', days: 0 },
  { label: '最近3天', days: 3 },
  { label: '最近7天', days: 7 },
  { label: '最近30天', days: 30 },
];

export function AdvancedFilterDrawer({ isOpen, onClose }: AdvancedFilterDrawerProps) {
  const { filters, setFilters, resetFilters } = useTaskStore();
  
  // 本地状态
  const [localFilters, setLocalFilters] = useState<TaskFilters>(filters);
  const [datePreset, setDatePreset] = useState<string>('');

  // 同步filters到本地状态
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  // 应用筛选
  const handleApply = () => {
    setFilters(localFilters);
    onClose();
  };

  // 重置筛选
  const handleReset = () => {
    setLocalFilters({});
    setDatePreset('');
    resetFilters();
    onClose();
  };

  // 应用日期预设
  const handleDatePreset = (days: number) => {
    const endDate = new Date();
    const startDate = new Date();
    
    if (days === 0) {
      // 今天
      startDate.setHours(0, 0, 0, 0);
    } else {
      // 最近N天
      startDate.setDate(startDate.getDate() - days);
    }
    
    setLocalFilters({
      ...localFilters,
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0],
    });
    setDatePreset(days === 0 ? 'today' : `last${days}days`);
  };

  // 自定义日期变化
  const handleDateChange = (field: 'start_date' | 'end_date', value: string) => {
    setLocalFilters({
      ...localFilters,
      [field]: value,
    });
    setDatePreset('');
  };

  // 获取活动筛选数量
  const getActiveFilterCount = () => {
    let count = 0;
    if (localFilters.status) count++;
    if (localFilters.filename) count++;
    if (localFilters.layout_mode) count++;
    if (localFilters.start_date || localFilters.end_date) count++;
    return count;
  };

  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩层 */}
      <div
        className="fixed inset-0 bg-gray-900/20 backdrop-blur-[2px] z-40 transition-opacity"
        onClick={onClose}
      />

      {/* 抽屉 */}
      <div className="fixed inset-y-0 right-0 w-full md:w-96 bg-white shadow-xl z-50 transform transition-transform">
        <div className="h-full flex flex-col">
          {/* 标题栏 */}
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-bold text-gray-900">高级筛选</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 筛选条件 */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* 任务状态 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                任务状态
              </label>
              <select
                value={localFilters.status || ''}
                onChange={(e) =>
                  setLocalFilters({
                    ...localFilters,
                    status: e.target.value || undefined,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 文件名搜索 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                文件名
              </label>
              <input
                type="text"
                value={localFilters.filename || ''}
                onChange={(e) =>
                  setLocalFilters({
                    ...localFilters,
                    filename: e.target.value || undefined,
                  })
                }
                placeholder="搜索文件名..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* 排版模式 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                排版模式
              </label>
              <select
                value={localFilters.layout_mode || ''}
                onChange={(e) =>
                  setLocalFilters({
                    ...localFilters,
                    layout_mode: e.target.value || undefined,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {LAYOUT_MODE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 时间范围 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                时间范围
              </label>
              
              {/* 快捷选项 */}
              <div className="flex flex-wrap gap-2 mb-3">
                {DATE_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => handleDatePreset(preset.days)}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      datePreset === (preset.days === 0 ? 'today' : `last${preset.days}days`)
                        ? 'bg-blue-50 border-blue-500 text-blue-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* 自定义日期范围 */}
              <div className="space-y-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">开始日期</label>
                  <input
                    type="date"
                    value={localFilters.start_date || ''}
                    onChange={(e) => handleDateChange('start_date', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">结束日期</label>
                  <input
                    type="date"
                    value={localFilters.end_date || ''}
                    onChange={(e) => handleDateChange('end_date', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* 活动筛选标签 */}
            {getActiveFilterCount() > 0 && (
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500">
                    已选择 {getActiveFilterCount()} 个筛选条件
                  </span>
                  <button
                    onClick={() => {
                      setLocalFilters({});
                      setDatePreset('');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    清除全部
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="p-6 border-t bg-gray-50">
            <div className="flex space-x-3">
              <button
                onClick={handleReset}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
              >
                重置
              </button>
              <button
                onClick={handleApply}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                应用筛选
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}