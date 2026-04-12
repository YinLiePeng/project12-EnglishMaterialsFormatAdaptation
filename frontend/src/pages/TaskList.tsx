import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTaskStore } from '../store/taskStore';
import { Button } from '../components/common/Button';
import { StatisticsPanel } from '../components/task/StatisticsPanel';
import { AdvancedFilterDrawer } from '../components/task/AdvancedFilterDrawer';
import { cancelTask, getDownloadUrl } from '../services/api';
import type { TaskStatus, TaskSort } from '../types';

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '等待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '处理失败',
};

const LAYOUT_MODE_LABELS: Record<string, string> = {
  none: '无模板排版',
  empty: '空模板排版',
  complete: '完整模板排版',
};

const PRESET_STYLE_LABELS: Record<string, string> = {
  universal: '通用排版',
  primary_low: '小学低年级护眼版',
  primary_high: '小学高年级版',
  junior: '初中通用版',
  senior: '高中通用版',
  exam: '模拟试卷版',
  lecture: '专题讲义版',
  essay: '作文范文版',
  preserve: '保留原格式',
};

const SORT_OPTIONS: Array<{ value: TaskSort['by']; label: string }> = [
  { value: 'created_at', label: '创建时间' },
  { value: 'processing_time', label: '处理时长' },
  { value: 'input_filename', label: '文件名' },
];

export function TaskList() {
  const navigate = useNavigate();
  const {
    tasks,
    total,
    page,
    pageSize,
    loading,
    error,
    selectedTaskIds,
    fetchTasks,
    setPage,
    setFilters,
    setSort,
    toggleTaskSelection,
    selectAllTasks,
    clearSelection,
    deleteSelectedTasks,
    clearError,
  } = useTaskStore();

  const [selectedTask, setSelectedTask] = useState<TaskStatus | null>(null);
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [sortBy, setSortBy] = useState<TaskSort['by']>('created_at');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // 初始化和筛选条件变化时获取任务
  useEffect(() => {
    fetchTasks();
  }, [page, pageSize]);

  // 排序变化时重新获取
  useEffect(() => {
    setSort({ by: sortBy, order: sortOrder });
    fetchTasks();
  }, [sortBy, sortOrder]);

  const handleCancel = async (taskId: string) => {
    if (!confirm('确定要取消这个任务吗？')) {
      return;
    }
    try {
      await cancelTask(taskId);
      fetchTasks();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      alert(error.response?.data?.message || '取消任务失败');
    }
  };

  const handleViewDetail = (task: TaskStatus) => {
    setSelectedTask(task);
  };

  const handleCloseDetail = () => {
    setSelectedTask(null);
  };

  const handleDownload = (taskId: string) => {
    window.open(getDownloadUrl(taskId), '_blank');
  };

  const handleSortChange = (newSortBy: TaskSort['by']) => {
    if (newSortBy === sortBy) {
      // 切换排序方向
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // 新的排序字段，默认降序
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
  };

  const handleBatchDelete = async () => {
    setDeleteLoading(true);
    try {
      const result = await deleteSelectedTasks();
      alert(`成功删除 ${result.deleted_count} 个任务，清理 ${result.deleted_files} 个文件`);
      setDeleteDialogOpen(false);
      clearSelection();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } | { message?: string } };
      const errorMessage = 
        (error.response as { data?: { message?: string } })?.data?.message ||
        (error.response as { message?: string })?.message ||
        (error as { message?: string }).message ||
        '批量删除失败';
      alert(errorMessage);
    } finally {
      setDeleteLoading(false);
    }
  };

  const isAllSelected = tasks.length > 0 && selectedTaskIds.size === tasks.length;
  const isSomeSelected = selectedTaskIds.size > 0 && !isAllSelected;

  const totalPages = Math.ceil(total / pageSize);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* 统计面板 */}
        <StatisticsPanel />

        {/* 标题和操作 */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">任务列表</h1>
            <p className="text-gray-500 mt-1">查看和管理所有处理任务</p>
          </div>
          <div className="mt-4 sm:mt-0 flex space-x-3">
            <Button variant="outline" onClick={fetchTasks} loading={loading}>
              刷新
            </Button>
            <Button onClick={() => navigate('/')}>新建任务</Button>
          </div>
        </div>

        {/* 工具栏 */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4 items-center">
            {/* 搜索框 */}
            <div className="flex-1 w-full lg:w-auto">
              <input
                type="text"
                placeholder="搜索文件名..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onChange={(e) => {
                  setFilters({ filename: e.target.value || undefined });
                  setPage(1);
                  fetchTasks();
                }}
              />
            </div>

            {/* 排序选择 */}
            <div className="flex items-center space-x-2 w-full lg:w-auto">
              <select
                value={sortBy}
                onChange={(e) => handleSortChange(e.target.value as TaskSort['by'])}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                title={sortOrder === 'asc' ? '升序' : '降序'}
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>

            {/* 高级筛选按钮 */}
            <Button
              variant="outline"
              onClick={() => setIsFilterDrawerOpen(true)}
              className="w-full lg:w-auto"
            >
              高级筛选
            </Button>

            {/* 批量删除按钮 */}
            {selectedTaskIds.size > 0 && (
              <Button
                variant="danger"
                onClick={() => setDeleteDialogOpen(true)}
                className="w-full lg:w-auto"
              >
                批量删除 ({selectedTaskIds.size})
              </Button>
            )}
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={clearError} className="text-red-800 hover:text-red-900">
              ×
            </button>
          </div>
        )}

        {/* 任务列表 */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={isAllSelected}
                      ref={(input) => {
                        if (isSomeSelected && input) {
                          input.indeterminate = true;
                        }
                      }}
                      onChange={() => (isAllSelected ? clearSelection() : selectAllTasks())}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    任务ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    创建时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    处理用时
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center">
                      <div className="flex justify-center">
                        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      </div>
                    </td>
                  </tr>
                ) : tasks.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      暂无任务记录
                    </td>
                  </tr>
                ) : (
                  tasks.map((task) => (
                    <tr
                      key={task.task_id}
                      className={`hover:bg-gray-50 ${selectedTaskIds.has(task.task_id) ? 'bg-blue-50' : ''}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={selectedTaskIds.has(task.task_id)}
                          onChange={() => toggleTaskSelection(task.task_id)}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                        {task.task_id.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="max-w-xs truncate" title={task.input_filename}>
                          {task.input_filename}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_STYLES[task.status]}`}
                        >
                          {STATUS_LABELS[task.status]}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(task.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {task.processing_time != null ? `${task.processing_time}秒` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleViewDetail(task)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            详情
                          </button>
                          {task.status === 'completed' && (
                            <>
                              <button
                                onClick={() => navigate(`/preview/${task.task_id}`)}
                                className="text-indigo-600 hover:text-indigo-900"
                              >
                                预览
                              </button>
                              <button
                                onClick={() => handleDownload(task.task_id)}
                                className="text-green-600 hover:text-green-900"
                              >
                                下载
                              </button>
                            </>
                          )}
                          {(task.status === 'pending' || task.status === 'processing') && (
                            <button
                              onClick={() => handleCancel(task.task_id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              取消
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="bg-white px-6 py-3 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                共 <span className="font-medium">{total}</span> 条记录，第{' '}
                <span className="font-medium">{page}</span> /{' '}
                <span className="font-medium">{totalPages}</span> 页
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 任务详情模态框 */}
        {selectedTask && (
          <div className="fixed inset-0 bg-gray-900/20 backdrop-blur-[2px] flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-xl font-bold text-gray-900">任务详情</h2>
                  <button
                    onClick={handleCloseDetail}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-500">任务ID</label>
                      <p className="mt-1 text-sm text-gray-900 font-mono">{selectedTask.task_id}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-500">状态</label>
                      <p className="mt-1">
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_STYLES[selectedTask.status]}`}
                        >
                          {STATUS_LABELS[selectedTask.status]}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-500">文件名</label>
                    <p className="mt-1 text-sm text-gray-900">{selectedTask.input_filename}</p>
                  </div>

                  {selectedTask.output_filename && (
                    <div>
                      <label className="block text-sm font-medium text-gray-500">输出文件</label>
                      <p className="mt-1 text-sm text-gray-900">{selectedTask.output_filename}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-500">排版模式</label>
                      <p className="mt-1 text-sm text-gray-900">{LAYOUT_MODE_LABELS[selectedTask.layout_mode] || selectedTask.layout_mode || '-'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-500">预设样式</label>
                      <p className="mt-1 text-sm text-gray-900">{PRESET_STYLE_LABELS[selectedTask.preset_style] || selectedTask.preset_style || '-'}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-500">创建时间</label>
                      <p className="mt-1 text-sm text-gray-900">{formatDate(selectedTask.created_at)}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-500">开始处理时间</label>
                      <p className="mt-1 text-sm text-gray-900">{formatDate(selectedTask.started_at)}</p>
                    </div>
                  </div>

                  {selectedTask.completed_at && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-500">完成时间</label>
                        <p className="mt-1 text-sm text-gray-900">
                          {formatDate(selectedTask.completed_at)}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">处理用时</label>
                        <p className="mt-1 text-sm text-gray-900">
                          {selectedTask.processing_time != null ? `${selectedTask.processing_time}秒` : '-'}
                        </p>
                      </div>
                    </div>
                  )}

                  {selectedTask.error_message && (
                    <div>
                      <label className="block text-sm font-medium text-gray-500">错误信息</label>
                      <p className="mt-1 text-sm text-red-600">{selectedTask.error_message}</p>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  {selectedTask.status === 'completed' && (
                    <Button onClick={() => handleDownload(selectedTask.task_id)}>下载文件</Button>
                  )}
                  <Button variant="outline" onClick={handleCloseDetail}>
                    关闭
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 高级筛选抽屉 */}
        <AdvancedFilterDrawer
          isOpen={isFilterDrawerOpen}
          onClose={() => setIsFilterDrawerOpen(false)}
        />

        {/* 批量删除确认对话框 */}
        {deleteDialogOpen && (
          <div className="fixed inset-0 bg-gray-900/20 backdrop-blur-[2px] flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">确认批量删除</h3>
                <p className="text-gray-600 mb-6">
                  确定要删除选中的 <span className="font-bold">{selectedTaskIds.size}</span> 个任务吗？
                  <br />
                  <span className="text-sm text-red-600">
                    此操作将同时删除相关的文件，且无法恢复。包括等待中、处理中、已完成和失败的所有任务。
                  </span>
                </p>
                <div className="flex justify-end space-x-3">
                  <Button
                    variant="outline"
                    onClick={() => setDeleteDialogOpen(false)}
                    disabled={deleteLoading}
                  >
                    取消
                  </Button>
                  <Button
                    variant="danger"
                    onClick={handleBatchDelete}
                    loading={deleteLoading}
                  >
                    确认删除
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}