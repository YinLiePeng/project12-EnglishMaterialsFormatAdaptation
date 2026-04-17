import { useEffect } from 'react';
import { useTaskStore } from '../../store/taskStore';

export function StatisticsPanel() {
  const { statistics, statisticsLoading, fetchStatistics } = useTaskStore();

  useEffect(() => {
    fetchStatistics();
  }, [fetchStatistics]);

  if (statisticsLoading || !statistics) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-lg shadow-sm p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    { label: '总任务', value: statistics.total, color: 'text-blue-600' },
    { label: '等待中', value: statistics.status_stats.pending, color: 'text-yellow-600' },
    { label: '处理中', value: statistics.status_stats.processing, color: 'text-indigo-600' },
    { label: '已完成', value: statistics.status_stats.completed, color: 'text-green-600' },
    { label: '失败', value: statistics.status_stats.failed, color: 'text-red-600' },
    { label: '今日新增', value: statistics.today_count, color: 'text-purple-600' },
  ];

  return (
    <div className="mb-6">
      {/* 主统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow"
          >
            <div className="text-sm text-gray-500 mb-1">{stat.label}</div>
            <div className={`text-2xl font-bold ${stat.color}`}>
              {stat.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* 详细统计信息 */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 本周统计 */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">本周任务</div>
              <div className="text-xl font-bold text-gray-900 mt-1">
                {statistics.week_count}
              </div>
            </div>
            <div className="text-3xl">📊</div>
          </div>
        </div>

        {/* 成功率 */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">成功率</div>
              <div className="text-xl font-bold text-green-600 mt-1">
                {statistics.success_rate}%
              </div>
            </div>
            <div className="text-3xl">✓</div>
          </div>
        </div>

        {/* 平均处理时间 */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">平均处理时间</div>
              <div className="text-xl font-bold text-indigo-600 mt-1">
                {statistics.avg_processing_time}秒
              </div>
            </div>
            <div className="text-3xl">⚡</div>
          </div>
        </div>
      </div>
    </div>
  );
}