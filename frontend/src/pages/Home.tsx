import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropzone } from '../components/upload/FileDropzone';
import { ModeSelector } from '../components/template/ModeSelector';
import { PresetGallery } from '../components/template/PresetGallery';
import { StylePreviewDrawer } from '../components/template/StylePreviewDrawer';
import TemplatePreview from '../components/template/TemplatePreview';
import { Button } from '../components/common/Button';
import { useUploadStore } from '../store/uploadStore';
import { getPresetStyles, uploadFile, getTemplatePreview } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import type { PresetStyle, MarkerPosition } from '../types';

const FEATURE_OPTIONS = [
  {
    id: 'cleaning',
    title: '内容清洗',
    description: '自动清除广告、水印、URL等垃圾内容',
    detail: '采用「规则过滤为主，大模型校验为辅」的双层安全机制。第一层通过确定性规则批量过滤格式特征明确的垃圾内容（网站广告、水印文字、二维码转译文本、免责声明、版权标注、无关网址、乱码字符等），无任何误删风险；第二层通过大模型做语义层面的二次校验，识别规则无法覆盖的隐性垃圾内容，同时严格规避有效教学内容的误删。',
  },
  {
    id: 'correction',
    title: '内容纠错',
    description: '自动修正标点混用、多余空格等问题',
    detail: '遵循「安全优先、权责清晰」原则，严格区分自动修正与标注预警。仅对无歧义的基础错误进行自动修正（拼写错误、中英文标点全角半角不规范、多余空格与换行符、乱码字符、音标显示异常等），全部修正内容在最终文档中以 Word 修订模式留痕。对于可能影响原题题意的内容，仅做标注预警，不自动修改，最终决定权完全交给教师。',
  },
  {
    id: 'llm',
    title: '大模型语义识别',
    description: '调用DeepSeek进行语义分析，提高识别准确率',
    detail: '启用后，系统将调用大语言模型对原始资料进行语义层面的结构识别与内容理解，显著提升对复杂排版、非标准格式的识别准确率。大模型仅输出标准化结构化指令，不直接控制格式参数。启用后处理时间会有所增加。',
  },
];

function InfoPopover({ content }: { content: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(!open); }}
        className="w-4 h-4 rounded-full inline-flex items-center justify-center text-gray-300 hover:text-blue-500 hover:bg-blue-50 transition-colors flex-shrink-0"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 w-72 p-3 bg-white rounded-lg shadow-lg border border-gray-100 text-xs text-gray-600 leading-relaxed z-50">
          {content}
        </div>
      )}
    </div>
  );
}

export function Home() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const {
    file,
    template,
    layoutMode,
    presetStyle,
    templatePreview,
    templatePreviewLoading,
    templatePreviewError,
    markerPosition,
    setFile,
    setTemplate,
    setLayoutMode,
    setPresetStyle,
    setCurrentTaskId,
    setTemplatePreview,
    setTemplatePreviewLoading,
    setTemplatePreviewError,
    setMarkerPosition,
  } = useUploadStore();

  const [presets, setPresets] = useState<PresetStyle[]>([]);
  const [uploading, setUploading] = useState(false);
  const [useLLM, setUseLLM] = useState(false);
  const [enableCleaning, setEnableCleaning] = useState(false);
  const [enableCorrection, setEnableCorrection] = useState(false);
  const [previewStyleId, setPreviewStyleId] = useState<string | null>(null);

  const isPreserve = presetStyle === 'preserve';
  const isPdf = file?.name.toLowerCase().endsWith('.pdf') ?? false;

  useEffect(() => {
    if (isPreserve) setUseLLM(false);
  }, [isPreserve]);

  useEffect(() => {
    getPresetStyles()
      .then(setPresets)
      .catch(() => setPresets([]));
  }, []);

  useEffect(() => {
    if (layoutMode === 'empty' && template) {
      setMarkerPosition(null);
      setTemplatePreviewLoading(true);
      setTemplatePreviewError(null);
      getTemplatePreview(template)
        .then((data) => {
          setTemplatePreview(data);
          setTemplatePreviewLoading(false);
        })
        .catch((err: unknown) => {
          const apiError = err as { response?: { data?: { message?: string } } };
          setTemplatePreviewError(apiError.response?.data?.message || '模板预览失败');
          setTemplatePreview(null);
          setTemplatePreviewLoading(false);
        });
    } else {
      setTemplatePreview(null);
      setTemplatePreviewError(null);
      setMarkerPosition(null);
    }
  }, [layoutMode, template, setTemplatePreview, setTemplatePreviewLoading, setTemplatePreviewError, setMarkerPosition]);

  const handleStart = async () => {
    if (!file) {
      showToast('请先上传文件', 'error');
      return;
    }

    if (layoutMode === 'empty' && !template) {
      showToast('空模板模式需要上传模板文件', 'error');
      return;
    }

    if (layoutMode === 'empty' && !markerPosition) {
      showToast('请在模板预览中选择内容填充位置', 'error');
      return;
    }

    if (layoutMode === 'complete' && !template) {
      showToast('完整模板模式需要上传模板文件', 'error');
      return;
    }

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
        marker_position: markerPosition ? JSON.stringify(markerPosition) : undefined,
      });

      setCurrentTaskId(result.task_id);
      navigate('/process');
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { message?: string } } };
      showToast(apiError.response?.data?.message || '上传失败，请重试', 'error');
    } finally {
      setUploading(false);
    }
  };

  const featureStateMap: Record<string, { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }> = {
    cleaning: { checked: enableCleaning, onChange: setEnableCleaning },
    correction: { checked: enableCorrection, onChange: setEnableCorrection },
    llm: { checked: useLLM, onChange: setUseLLM, disabled: isPreserve },
  };

  const handleMarkerSelect = (pos: MarkerPosition | null) => {
    if (pos === null) {
      setMarkerPosition(null);
    } else {
      setMarkerPosition(pos);
    }
  };

  return (
    <>
      <div className="max-w-5xl mx-auto px-4 py-4">
        <div className="space-y-2.5">
          {/* 步骤1：上传文件 */}
          <div className="bg-white rounded-lg shadow-sm p-3">
            <h2 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">1</span>
              上传原始教学资料
            </h2>
            <FileDropzone file={file} onClear={() => setFile(null)} onFileSelect={setFile} />
            {isPdf && (
              <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                <svg className="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs text-amber-700">
                  已选择PDF文件，系统将自动检测类型（原生/扫描/混合）并选择最佳处理方式
                </span>
              </div>
            )}
          </div>

          {/* 步骤2：选择排版模式 */}
          <div className="bg-white rounded-lg shadow-sm p-3">
            <h2 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">2</span>
              选择排版模式
            </h2>
            <ModeSelector value={layoutMode} onChange={setLayoutMode} />

            {(layoutMode === 'empty' || layoutMode === 'complete') && (
              <div className="mt-2 p-2.5 bg-gray-50 rounded-lg">
                <FileDropzone file={template} onClear={() => setTemplate(null)} onFileSelect={setTemplate} />
              </div>
            )}
          </div>

          {/* 步骤2.5：模板预览与标记位选择（仅空模板模式） */}
          {layoutMode === 'empty' && template && (
            <div className="bg-white rounded-lg shadow-sm p-3">
              <h2 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">3</span>
                选择内容填充位置
                <span className="text-xs text-gray-400 font-normal">（点击模板中的目标位置）</span>
              </h2>
              {templatePreviewLoading && (
                <div className="flex items-center justify-center py-8">
                  <svg className="animate-spin h-5 w-5 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-sm text-gray-500">正在解析模板...</span>
                </div>
              )}
              {templatePreviewError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="text-sm text-red-800 font-medium">模板解析失败</div>
                  <div className="text-xs text-red-600 mt-1">{templatePreviewError}</div>
                </div>
              )}
              {templatePreview && !templatePreviewLoading && (
                <TemplatePreview
                  preview={templatePreview}
                  markerPosition={markerPosition}
                  onMarkerSelect={handleMarkerSelect}
                />
              )}
            </div>
          )}

          {/* 步骤3/4：选择排版样式（仅非完整模板模式） */}
          {layoutMode !== 'complete' && (
            <div className="bg-white rounded-lg shadow-sm p-3">
              <h2 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">
                  {layoutMode === 'empty' ? '4' : '3'}
                </span>
                选择排版样式
              </h2>
              <PresetGallery
                presets={presets}
                value={presetStyle}
                onChange={setPresetStyle}
                onPreview={(styleId) => setPreviewStyleId(styleId)}
              />
            </div>
          )}

          {/* 步骤4：功能选项（可选） */}
          <div className="bg-white rounded-lg shadow-sm p-3">
            <h2 className="text-sm font-medium text-gray-900 mb-2.5 flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">
                {layoutMode === 'complete' ? '3' : layoutMode === 'empty' ? '5' : '4'}
              </span>
              功能选项
              <span className="text-xs text-gray-400 font-normal">（可选，按需勾选）</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {FEATURE_OPTIONS.map((feature) => {
                const state = featureStateMap[feature.id];
                return (
                  <label
                    key={feature.id}
                    className={`flex items-start gap-2.5 p-3 rounded-lg border-2 transition-all ${
                      state.disabled
                        ? 'border-gray-100 bg-gray-50/50 opacity-50 cursor-not-allowed'
                        : state.checked
                          ? 'border-blue-500 bg-blue-50/50 cursor-pointer'
                          : 'border-gray-100 hover:border-gray-200 cursor-pointer'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={state.checked}
                      onChange={(e) => state.onChange(e.target.checked)}
                      disabled={state.disabled}
                      className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium text-gray-900">{feature.title}</span>
                        <InfoPopover content={feature.detail} />
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{feature.description}</p>
                      {feature.id === 'llm' && !state.disabled && (
                        <p className="text-xs text-orange-500 mt-1">启用后可能增加处理时间</p>
                      )}
                      {feature.id === 'llm' && state.disabled && (
                        <p className="text-xs text-gray-400 mt-1">保留原格式下不需要</p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* 开始按钮 */}
          <Button
            size="lg"
            onClick={handleStart}
            loading={uploading}
            className="w-full"
          >
            开始处理
          </Button>
        </div>
      </div>

      <StylePreviewDrawer
        isOpen={previewStyleId !== null}
        onClose={() => setPreviewStyleId(null)}
        styleId={previewStyleId || ''}
        styles={presets}
        onApply={(styleId) => {
          setPresetStyle(styleId);
          setPreviewStyleId(null);
        }}
      />
    </>
  );
}
