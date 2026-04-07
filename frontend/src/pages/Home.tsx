import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropzone } from '../components/upload/FileDropzone';
import { ModeSelector } from '../components/template/ModeSelector';
import { PresetGallery } from '../components/template/PresetGallery';
import { Button } from '../components/common/Button';
import { useUploadStore } from '../store/uploadStore';
import { getPresetStyles, uploadFile } from '../services/api';
import type { PresetStyle } from '../types';

export function Home() {
  const navigate = useNavigate();
  const {
    file,
    template,
    layoutMode,
    presetStyle,
    setFile,
    setTemplate,
    setLayoutMode,
    setPresetStyle,
    setCurrentTaskId,
  } = useUploadStore();

  const [presets, setPresets] = useState<PresetStyle[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useLLM, setUseLLM] = useState(false);
  const [enableCleaning, setEnableCleaning] = useState(false);
  const [enableCorrection, setEnableCorrection] = useState(false);

  // 获取预设样式
  useEffect(() => {
    getPresetStyles()
      .then(setPresets)
      .catch(() => setPresets([]));
  }, []);

  // 开始处理
  const handleStart = async () => {
    if (!file) {
      setError('请先上传文件');
      return;
    }

    if (layoutMode === 'empty' && !template) {
      setError('空模板模式需要上传模板文件');
      return;
    }

    if (layoutMode === 'complete' && !template) {
      setError('完整模板模式需要上传模板文件');
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const result = await uploadFile({
        file,
        template: template || undefined,
        layout_mode: layoutMode,
        preset_style: layoutMode === 'complete' ? undefined : presetStyle,
        enable_cleaning: enableCleaning,
        enable_correction: enableCorrection,
        use_llm: useLLM,
      });

      setCurrentTaskId(result.task_id);
      navigate('/process');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      setError(error.response?.data?.message || '上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            英语教学资料智能格式适配工具
          </h1>
          <p className="text-gray-500 mt-2">
            一站式解决教学资料的智能清洗、格式迁移适配、分级内容纠错
          </p>
        </div>

        {/* 步骤1：上传文件 */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            步骤1：上传原始教学资料
          </h2>
          <FileDropzone onFileSelect={setFile} />
          {file && (
            <div className="mt-3 flex items-center text-sm text-green-600">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              已选择：{file.name}
            </div>
          )}
        </div>

        {/* 步骤2：选择排版模式 */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            步骤2：选择排版模式
          </h2>
          <ModeSelector value={layoutMode} onChange={setLayoutMode} />

          {/* 空模板或完整模板需要上传模板 */}
          {(layoutMode === 'empty' || layoutMode === 'complete') && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                上传{layoutMode === 'empty' ? '空模板' : '完整模板'}文件
              </h3>
              <FileDropzone onFileSelect={setTemplate} />
              {template && (
                <div className="mt-2 text-sm text-green-600">
                  已选择：{template.name}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 步骤3：选择预设样式（仅无模板模式） */}
        {layoutMode !== 'complete' && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              步骤3：选择排版样式
            </h2>
            <PresetGallery
              presets={presets}
              value={presetStyle}
              onChange={setPresetStyle}
            />

            {/* 处理选项 */}
            <div className="mt-6 pt-4 border-t border-gray-200 space-y-4">
              {/* 内容清洗选项 */}
              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableCleaning}
                  onChange={(e) => setEnableCleaning(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mt-0.5"
                />
                <div className="ml-3">
                  <span className="text-sm font-medium text-gray-700">
                    内容清洗（可选）
                  </span>
                  <p className="text-xs text-gray-500 mt-1">
                    自动清除广告、水印、URL等垃圾内容，保留有效教学内容。
                  </p>
                </div>
              </label>

              {/* 内容纠错选项 */}
              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableCorrection}
                  onChange={(e) => setEnableCorrection(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mt-0.5"
                />
                <div className="ml-3">
                  <span className="text-sm font-medium text-gray-700">
                    内容纠错（可选）
                  </span>
                  <p className="text-xs text-gray-500 mt-1">
                    自动修正标点混用、多余空格等问题，拼写错误仅标注不自动修改。
                  </p>
                </div>
              </label>

              {/* 大模型选项 */}
              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={useLLM}
                  onChange={(e) => setUseLLM(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mt-0.5"
                />
                <div className="ml-3">
                  <span className="text-sm font-medium text-gray-700">
                    启用大模型语义识别（可选）
                  </span>
                  <p className="text-xs text-gray-500 mt-1">
                    对于格式特征不明显的段落，调用DeepSeek大模型进行语义分析，提高识别准确率。
                    <span className="text-orange-500"> 启用后可能增加处理时间。</span>
                  </p>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
            {error}
          </div>
        )}

        {/* 开始按钮 */}
        <div className="flex justify-center">
          <Button
            size="lg"
            onClick={handleStart}
            loading={uploading}
            disabled={!file}
          >
            开始处理
          </Button>
        </div>

        {/* 快速开始说明 */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-800 mb-2">快速开始</h3>
          <ol className="text-sm text-blue-700 space-y-1">
            <li>1. 上传原始教学资料（支持DOCX格式）</li>
            <li>2. 选择排版模式（无模板/空模板/完整模板）</li>
            <li>3. 选择排版样式</li>
            <li>4. 点击开始处理，等待完成</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
