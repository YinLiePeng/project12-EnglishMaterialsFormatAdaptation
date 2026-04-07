import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUploadStore } from '../store/uploadStore';
import { useTaskPolling } from '../hooks/useTaskPolling';
import { Button } from '../components/common/Button';
import type { TaskStatus } from '../types';

const STAGES = [
  { key: 'pending', label: '等待处理' },
  { key: 'processing', label: '解析文件' },
  { key: 'formatting', label: '格式化中' },
  { key: 'generating', label: '生成文档' },
  { key: 'completed', label: '处理完成' },
];

export function Process() {
  const navigate = useNavigate();
  const { currentTaskId, taskStatus, setTaskStatus } = useUploadStore();
  const [progress, setProgress] = useState(0);

  // 轮询任务状态
  const handleStatusUpdate = useCallback((status: TaskStatus) => {
    setTaskStatus(status);

    // 根据状态更新进度
    if (status.status === 'pending') {
      setProgress(10);
    } else if (status.status === 'processing') {
      setProgress(50);
    }
  }, [setTaskStatus]);

  const handleComplete = useCallback((status: TaskStatus) => {
    if (status.status === 'completed') {
      setProgress(100);
    } else {
      // 处理失败
      setProgress(0);
    }
  }, []);

  useTaskPolling({
    taskId: currentTaskId,
    interval: 2000,
    onSuccess: handleStatusUpdate,
    onComplete: handleComplete,
  });

  // 如果没有任务ID，返回首页
  if (!currentTaskId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">没有正在进行的任务</p>
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </div>
      </div>
    );
  }

  const isCompleted = taskStatus?.status === 'completed';
  const isFailed = taskStatus?.status === 'failed';
  const isProcessing = taskStatus?.status === 'processing' || taskStatus?.status === 'pending';

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-sm p-8">
          {/* 标题 */}
          <div className="text-center mb-8">
            {isCompleted ? (
              <>
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-green-600"
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
              </>
            ) : isFailed ? (
              <>
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-red-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-red-600">处理失败</h1>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900">处理中...</h1>
              </>
            )}
          </div>

          {/* 进度条 */}
          <div className="mb-8">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-600'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500 text-center mt-2">{progress}%</p>
          </div>

          {/* 处理阶段 */}
          {isProcessing && (
            <div className="space-y-3 mb-8">
              {STAGES.map((stage, index) => {
                const stageProgress = (index + 1) * 20;
                const isActive = progress >= stageProgress - 10 && progress < stageProgress;
                const isDone = progress >= stageProgress;

                return (
                  <div key={stage.key} className="flex items-center">
                    {isDone ? (
                      <svg
                        className="w-5 h-5 text-green-500 mr-3"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : isActive ? (
                      <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-3" />
                    ) : (
                      <div className="w-5 h-5 border-2 border-gray-300 rounded-full mr-3" />
                    )}
                    <span className={isDone ? 'text-green-600' : isActive ? 'text-blue-600' : 'text-gray-400'}>
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

           {/* 处理结果信息 */}
           {taskStatus && (
             <div className="bg-gray-50 rounded-lg p-4 mb-6">
               <h3 className="text-sm font-medium text-gray-700 mb-2">任务信息</h3>
               <div className="text-sm text-gray-600 space-y-1">
                 <p>文件名：{taskStatus.input_filename}</p>
                 <p>任务ID：{taskStatus.task_id}</p>
                 {taskStatus.processing_time && (
                   <p>处理用时：{taskStatus.processing_time}秒</p>
                 )}
               </div>
             </div>
           )}

           {/* 错误信息 */}
          {isFailed && taskStatus?.error_message && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <h3 className="text-sm font-medium text-red-800 mb-1">错误信息</h3>
              <p className="text-sm text-red-600">{taskStatus.error_message}</p>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-center space-x-4">
            {isCompleted ? (
              <>
                <Button variant="outline" onClick={() => navigate(`/preview/${currentTaskId}`)}>
                  📄 查看解析预览
                </Button>
                <Button onClick={() => navigate('/result')}>查看结果</Button>
              </>
            ) : isFailed ? (
              <>
                <Button variant="outline" onClick={() => navigate('/')}>
                  重新上传
                </Button>
                <Button onClick={() => navigate('/')}>返回首页</Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => navigate('/')}>
                取消并返回
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
