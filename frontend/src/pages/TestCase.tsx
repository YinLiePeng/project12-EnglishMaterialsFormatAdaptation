import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropzone } from '../components/upload/FileDropzone';
import { Button } from '../components/common/Button';
import { submitTestCase } from '../services/api';

const PROBLEM_TYPES = ['格式问题', '内容丢失', '排版错误', '其他'];

export function TestCase() {
  const navigate = useNavigate();
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [outputFile, setOutputFile] = useState<File | null>(null);
  const [feedbackDescription, setFeedbackDescription] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [contactInfo, setContactInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTypeToggle = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSubmit = async () => {
    if (!originalFile) {
      setError('请上传原始文件');
      return;
    }

    if (!feedbackDescription.trim()) {
      setError('请填写反馈描述');
      return;
    }

    if (selectedTypes.length === 0) {
      setError('请选择至少一个问题类型');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      await submitTestCase({
        original_file: originalFile,
        feedback_description: feedbackDescription,
        problem_types: selectedTypes,
        output_file: outputFile || undefined,
        contact_info: contactInfo || undefined,
      });

      setSuccess(true);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      setError(error.response?.data?.message || '提交失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-2xl mx-auto px-4">
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
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
            <h1 className="text-2xl font-bold text-gray-900 mb-2">反馈提交成功！</h1>
            <p className="text-gray-500 mb-6">感谢您的帮助，我们会认真处理您的反馈</p>
            <Button onClick={() => navigate('/')}>返回首页</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">提交反馈</h1>
          <p className="text-gray-500 mb-6">对处理结果不满意？提交您遇到的问题，帮助我们改进</p>

          {/* 原始文件 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              原始文件 <span className="text-red-500">*</span>
            </label>
            <FileDropzone file={originalFile} onClear={() => setOriginalFile(null)} onFileSelect={setOriginalFile} />
          </div>

          {/* 输出文件（可选） */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              输出文件（可选）
            </label>
            <FileDropzone file={outputFile} onClear={() => setOutputFile(null)} onFileSelect={setOutputFile} />
          </div>

          {/* 问题类型 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              问题类型 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {PROBLEM_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeToggle(type)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    selectedTypes.includes(type)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* 反馈描述 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              反馈描述 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={feedbackDescription}
              onChange={(e) => setFeedbackDescription(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="请详细描述您遇到的问题..."
            />
          </div>

          {/* 联系方式 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              联系方式（可选）
            </label>
            <input
              type="text"
              value={contactInfo}
              onChange={(e) => setContactInfo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="邮箱或其他联系方式，便于我们跟进问题"
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
              {error}
            </div>
          )}

          {/* 提交按钮 */}
          <div className="flex justify-center space-x-4">
            <Button variant="outline" onClick={() => navigate('/')}>
              返回
            </Button>
            <Button onClick={handleSubmit} loading={submitting}>
              提交反馈
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
