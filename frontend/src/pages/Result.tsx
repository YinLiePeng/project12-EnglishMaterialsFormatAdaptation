import { useNavigate } from 'react-router-dom';
import { useUploadStore } from '../store/uploadStore';
import { Button } from '../components/common/Button';
import { getDownloadUrl } from '../services/api';

export function Result() {
  const navigate = useNavigate();
  const { taskStatus, reset } = useUploadStore();

  // 如果没有任务状态，返回首页
  if (!taskStatus || taskStatus.status !== 'completed') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">没有可下载的结果</p>
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </div>
      </div>
    );
  }

  const downloadUrl = getDownloadUrl(taskStatus.task_id);

  // 处理新文件
  const handleNewFile = () => {
    reset();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-sm p-8">
          {/* 成功图标 */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-10 h-10 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">处理完成！</h1>
          </div>

          {/* 处理统计 */}
          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">处理统计</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-blue-600">
                  {taskStatus.processing_time || 0}秒
                </p>
                <p className="text-sm text-gray-500">处理用时</p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <p className="text-2xl font-bold text-green-600">
                  {taskStatus.input_filename}
                </p>
                <p className="text-sm text-gray-500">原始文件</p>
              </div>
            </div>
          </div>

          {/* 文件信息 */}
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <svg
                className="w-5 h-5 text-blue-600 mt-0.5 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="text-sm text-blue-700">
                <p className="font-medium">说明：</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>下载的文件包含Word原生修订和批注</li>
                  <li>您可以在Word中一键接受/驳回单条修订</li>
                  <li>批注内容为疑似问题，仅供参考</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-col sm:flex-row justify-center space-y-3 sm:space-y-0 sm:space-x-4">
            <a
              href={downloadUrl}
              download={taskStatus.output_filename || 'formatted.docx'}
              className="inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <svg
                className="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              下载文件
            </a>
            <Button variant="outline" onClick={() => navigate(`/preview/${taskStatus.task_id}`)}>
              📄 查看解析预览
            </Button>
            <Button variant="outline" onClick={handleNewFile}>
              处理新文件
            </Button>
          </div>

          {/* 提交反馈 */}
          <div className="mt-8 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-500 mb-2">
              对结果不满意？
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/feedback')}
            >
              提交反馈帮助我们改进
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
