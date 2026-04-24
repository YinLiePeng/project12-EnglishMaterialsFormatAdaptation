import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/common/EmptyState';
import { 
  getTestCaseList, 
  getTestCaseDetail, 
  deleteTestCase, 
  updateTestCaseStatus,
  getTestCaseOriginalUrl,
  getTestCaseOutputUrl
} from '../services/api';
import type { TestCase, TestCaseDetail } from '../types';

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待处理' },
  { value: 'processing', label: '处理中' },
  { value: 'resolved', label: '已解决' },
  { value: 'rejected', label: '已拒绝' },
];

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  rejected: '已拒绝',
};

const PROBLEM_TYPE_STYLES: Record<string, string> = {
  '格式问题': 'bg-purple-100 text-purple-800',
  '内容丢失': 'bg-orange-100 text-orange-800',
  '排版错误': 'bg-blue-100 text-blue-800',
  '其他': 'bg-gray-100 text-gray-800',
};

export function TestCaseManagement() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [testcases, setTestcases] = useState<TestCase[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTestcase, setSelectedTestcase] = useState<TestCaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [statusUpdateData, setStatusUpdateData] = useState({
    status: '',
    adminNotes: '',
  });

  const fetchTestcases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getTestCaseList({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      });
      setTestcases(response.testcases);
      setTotal(response.total);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      setError(error.response?.data?.message || '获取测试用例列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter]);

  useEffect(() => {
    fetchTestcases();
  }, [fetchTestcases]);

  const handleViewDetail = async (testcaseId: string) => {
    setDetailLoading(true);
    try {
      const detail = await getTestCaseDetail(testcaseId);
      setSelectedTestcase(detail);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      showToast(error.response?.data?.message || '获取测试用例详情失败', 'error');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedTestcase(null);
  };

  const handleDelete = async (testcaseId: string) => {
    setDeleteTargetId(testcaseId);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTargetId) return;
    try {
      await deleteTestCase(deleteTargetId);
      showToast('测试用例已删除', 'success');
      fetchTestcases();
      if (selectedTestcase?.id === deleteTargetId) {
        setSelectedTestcase(null);
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      showToast(error.response?.data?.message || '删除测试用例失败', 'error');
    } finally {
      setDeleteTargetId(null);
    }
  };

  const handleOpenStatusModal = (testcase: TestCase | TestCaseDetail) => {
    setStatusUpdateData({
      status: testcase.status,
      adminNotes: (testcase as TestCaseDetail).admin_notes || '',
    });
    setShowStatusModal(true);
  };

  const handleUpdateStatus = async () => {
    if (!selectedTestcase) return;
    try {
      await updateTestCaseStatus(
        selectedTestcase.id,
        statusUpdateData.status,
        statusUpdateData.adminNotes || undefined
      );
      setShowStatusModal(false);
      // 刷新详情
      const detail = await getTestCaseDetail(selectedTestcase.id);
      setSelectedTestcase(detail);
      // 刷新列表
      fetchTestcases();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      showToast(error.response?.data?.message || '更新状态失败', 'error');
    }
  };

  const filteredTestcases = testcases.filter((testcase) =>
    testcase.feedback_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    testcase.original_filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPages = Math.ceil(total / pageSize);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* 标题和操作 */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">测试用例管理</h1>
            <p className="text-gray-500 mt-1">查看和管理用户提交的反馈</p>
          </div>
          <div className="mt-4 sm:mt-0 flex space-x-3">
            <Button variant="outline" onClick={fetchTestcases} loading={loading}>
              刷新
            </Button>
            <Button onClick={() => navigate('/feedback')}>提交反馈</Button>
          </div>
        </div>

        {/* 筛选和搜索 */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                搜索
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索文件名或反馈描述..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="w-full sm:w-48">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                状态筛选
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
            {error}
          </div>
        )}

        {/* 测试用例列表 */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    问题类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    提交时间
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="flex justify-center">
                        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      </div>
                    </td>
                  </tr>
                ) : filteredTestcases.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        title="暂无测试用例记录"
                        description="用户提交的反馈将显示在这里"
                      />
                    </td>
                  </tr>
                ) : (
                  filteredTestcases.map((testcase) => (
                    <tr key={testcase.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                        {testcase.id.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="max-w-xs truncate" title={testcase.original_filename}>
                          {testcase.original_filename}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-wrap gap-1">
                          {testcase.problem_types.map((type) => (
                            <span
                              key={type}
                              className={`px-2 py-1 text-xs font-medium rounded-full ${PROBLEM_TYPE_STYLES[type] || PROBLEM_TYPE_STYLES['其他']}`}
                            >
                              {type}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_STYLES[testcase.status]}`}>
                          {STATUS_LABELS[testcase.status]}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(testcase.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleViewDetail(testcase.id)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            详情
                          </button>
                          <button
                            onClick={() => handleDelete(testcase.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            删除
                          </button>
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
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 测试用例详情模态框 */}
        {selectedTestcase && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-xl font-bold text-gray-900">测试用例详情</h2>
                  <button
                    onClick={handleCloseDetail}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {detailLoading ? (
                  <div className="flex justify-center py-12">
                    <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* 基本信息 */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-500">ID</label>
                        <p className="mt-1 text-sm text-gray-900 font-mono">{selectedTestcase.id}</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">状态</label>
                        <p className="mt-1">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_STYLES[selectedTestcase.status]}`}>
                            {STATUS_LABELS[selectedTestcase.status]}
                          </span>
                        </p>
                      </div>
                    </div>

                    {/* 文件信息 */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-500">原始文件</label>
                        <p className="mt-1 text-sm text-gray-900">{selectedTestcase.original_filename}</p>
                        <a
                          href={getTestCaseOriginalUrl(selectedTestcase.id)}
                          download={selectedTestcase.original_filename}
                          className="mt-1 text-sm text-blue-600 hover:text-blue-800"
                        >
                          下载原始文件
                        </a>
                      </div>
                      {selectedTestcase.output_filename && (
                        <div>
                          <label className="block text-sm font-medium text-gray-500">输出文件</label>
                          <p className="mt-1 text-sm text-gray-900">{selectedTestcase.output_filename}</p>
                          <a
                            href={getTestCaseOutputUrl(selectedTestcase.id)}
                            download={selectedTestcase.output_filename}
                            className="mt-1 text-sm text-blue-600 hover:text-blue-800"
                          >
                            下载输出文件
                          </a>
                        </div>
                      )}
                    </div>

                    {/* 问题类型 */}
                    <div>
                      <label className="block text-sm font-medium text-gray-500">问题类型</label>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {selectedTestcase.problem_types.map((type) => (
                          <span
                            key={type}
                            className={`px-2 py-1 text-xs font-medium rounded-full ${PROBLEM_TYPE_STYLES[type] || PROBLEM_TYPE_STYLES['其他']}`}
                          >
                            {type}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* 反馈描述 */}
                    <div>
                      <label className="block text-sm font-medium text-gray-500">反馈描述</label>
                      <p className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
                        {selectedTestcase.feedback_description}
                      </p>
                    </div>

                    {/* 联系方式 */}
                    {selectedTestcase.contact_info && (
                      <div>
                        <label className="block text-sm font-medium text-gray-500">联系方式</label>
                        <p className="mt-1 text-sm text-gray-900">{selectedTestcase.contact_info}</p>
                      </div>
                    )}

                    {/* 管理员备注 */}
                    {selectedTestcase.admin_notes && (
                      <div>
                        <label className="block text-sm font-medium text-gray-500">管理员备注</label>
                        <p className="mt-1 text-sm text-gray-900">{selectedTestcase.admin_notes}</p>
                      </div>
                    )}

                    {/* 时间信息 */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-500">提交时间</label>
                        <p className="mt-1 text-sm text-gray-900">{formatDate(selectedTestcase.created_at)}</p>
                      </div>
                      {selectedTestcase.resolved_at && (
                        <div>
                          <label className="block text-sm font-medium text-gray-500">解决时间</label>
                          <p className="mt-1 text-sm text-gray-900">{formatDate(selectedTestcase.resolved_at)}</p>
                        </div>
                      )}
                    </div>

                    {/* 关联任务 */}
                    {selectedTestcase.task_id && (
                      <div>
                        <label className="block text-sm font-medium text-gray-500">关联任务</label>
                        <p className="mt-1 text-sm text-gray-900 font-mono">{selectedTestcase.task_id}</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-6 flex justify-between">
                  <div>
                    <Button
                      variant="outline"
                      onClick={() => handleOpenStatusModal(selectedTestcase)}
                    >
                      更新状态
                    </Button>
                  </div>
                  <div className="flex space-x-3">
                    <Button
                      variant="danger"
                      onClick={() => setDeleteTargetId(selectedTestcase.id)}
                    >
                      删除
                    </Button>
                    <Button variant="outline" onClick={handleCloseDetail}>
                      关闭
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 更新状态模态框 */}
        {showStatusModal && selectedTestcase && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">更新状态</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      状态
                    </label>
                    <select
                      value={statusUpdateData.status}
                      onChange={(e) => setStatusUpdateData({ ...statusUpdateData, status: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {STATUS_OPTIONS.filter((opt) => opt.value).map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      管理员备注
                    </label>
                    <textarea
                      value={statusUpdateData.adminNotes}
                      onChange={(e) => setStatusUpdateData({ ...statusUpdateData, adminNotes: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="添加备注信息（可选）"
                    />
                  </div>
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  <Button variant="outline" onClick={() => setShowStatusModal(false)}>
                    取消
                  </Button>
                  <Button onClick={handleUpdateStatus}>
                    保存
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 删除确认 */}
        {deleteTargetId && (
          <ConfirmDialog
            title="删除测试用例"
            message="确定要删除这个测试用例吗？此操作无法恢复。"
            confirmVariant="danger"
            confirmText="确认删除"
            onConfirm={handleDeleteConfirm}
            onCancel={() => setDeleteTargetId(null)}
          />
        )}
      </div>
    </div>
  );
}
