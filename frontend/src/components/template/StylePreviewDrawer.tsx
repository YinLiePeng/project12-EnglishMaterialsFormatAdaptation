import { useEffect, useState, useRef, useLayoutEffect } from 'react';
import type { PresetStyle } from '../../types';
import { generateStyleCSS, generatePaperStyles } from '../../utils/styleMapping';
import { SAMPLE_CONTENT } from '../../constants/sampleContent';
import { StyleParameters } from './StyleParameters';
import { Button } from '../common/Button';

interface StylePreviewDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  styleId: string;
  styles: PresetStyle[];
  onApply: (styleId: string) => void;
}

/**
 * 缩放指示器组件
 */
function ZoomIndicator({
  zoomLevel,
  onReset,
}: {
  zoomLevel: number;
  onReset: (level: number) => void;
}) {
  return (
    <div className="flex items-center justify-between mb-4 px-4 py-2 bg-gray-50 rounded-lg">
      {/* 缩放百分比 + 快捷键提示 */}
      <div className="flex items-center space-x-2">
        <span className="text-sm font-medium text-gray-700">{zoomLevel}%</span>
        <span className="text-xs text-gray-400 hidden sm:inline">
          Ctrl +/-号缩放
        </span>
      </div>

      {/* 快捷缩放按钮 */}
      <div className="flex items-center space-x-1">
        <button
          onClick={() => onReset(50)}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            zoomLevel === 50
              ? 'bg-blue-100 text-blue-700 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          50%
        </button>
        <button
          onClick={() => onReset(75)}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            zoomLevel === 75
              ? 'bg-blue-100 text-blue-700 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          75%
        </button>
        {zoomLevel !== 100 && (
          <button
            onClick={() => onReset(100)}
            className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium"
          >
            重置
          </button>
        )}
      </div>
    </div>
  );
}

export function StylePreviewDrawer({
  isOpen,
  onClose,
  styleId,
  styles,
  onApply,
}: StylePreviewDrawerProps) {
  const [currentStyle, setCurrentStyle] = useState<PresetStyle | null>(null);
  const [previewStyles, setPreviewStyles] = useState<any>(null);
  const [paperStyles, setPaperStyles] = useState<any>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(100); // 默认100%真实大小
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const zoomLevelRef = useRef(zoomLevel); // 使用ref存储最新的zoomLevel值，避免闭包陷阱

  // 同步 zoomLevel 到 ref
  useLayoutEffect(() => {
    zoomLevelRef.current = zoomLevel;
    console.log('[Zoom] zoomLevel updated:', zoomLevel);
  }, [zoomLevel]);

  // 加载样式配置
  useEffect(() => {
    if (styleId && styles.length > 0) {
      const style = styles.find((s) => s.id === styleId);
      if (style && style.config) {
        setCurrentStyle(style);
        setPreviewStyles(generateStyleCSS(style.config));
        setPaperStyles(generatePaperStyles(style.config.page));
      }
    }
  }, [styleId, styles]);

  // 滚轮缩放处理
  useEffect(() => {
    const container = previewContainerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      // 检测是否按下了 Ctrl 或 Cmd 键
      if (!e.ctrlKey && !e.metaKey) return;

      // 阻止浏览器默认缩放行为
      e.preventDefault();

      // 计算缩放方向（向下滚缩小，向上滚放大）
      const delta = e.deltaY > 0 ? -10 : 10;
      const newZoomLevel = Math.min(200, Math.max(50, zoomLevel + delta));

      setZoomLevel(newZoomLevel);
    };

    // 添加滚轮事件监听（passive: false 允许阻止默认行为）
    container.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      container.removeEventListener('wheel', handleWheel);
    };
  }, [zoomLevel]);

  // 键盘快捷键支持
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      // Ctrl/Cmd + Plus: 放大
      if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        setZoomLevel((prev) => Math.min(200, prev + 10));
      }

      // Ctrl/Cmd + Minus: 缩小
      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault();
        setZoomLevel((prev) => Math.max(50, prev - 10));
      }

      // Ctrl/Cmd + 0: 重置为100%
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        setZoomLevel(100);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // 移动端双指缩放支持
  const [touchDistance, setTouchDistance] = useState<number>(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      // 双指触摸
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      setTouchDistance(Math.sqrt(dx * dx + dy * dy));
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && touchDistance > 0) {
      // 阻止页面滚动
      // e.preventDefault(); // 注释掉，因为这会阻止页面滚动

      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const newDistance = Math.sqrt(dx * dx + dy * dy);

      // 计算缩放比例
      const scale = newDistance / touchDistance;
      const newZoomLevel = Math.min(200, Math.max(50, zoomLevel * scale));

      setZoomLevel(newZoomLevel);
      setTouchDistance(newDistance);
    }
  };

  const handleTouchEnd = () => {
    setTouchDistance(0);
  };

  if (!isOpen || !currentStyle || !previewStyles || !paperStyles) {
    return null;
  }

  return (
    <>
      {/* 遮罩层 */}
      <div
        className="fixed inset-0 bg-gray-900/20 backdrop-blur-[2px] z-40 transition-opacity"
        onClick={onClose}
      />

      {/* 抽屉 */}
      <div className="fixed inset-y-0 right-0 w-full md:w-[600px] lg:w-[800px] bg-white shadow-xl z-50 transform transition-transform">
        <div className="h-full flex flex-col">
          {/* 标题栏 */}
          <div className="flex items-center justify-between p-4 border-b">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {currentStyle.name} - 样式预览
              </h2>
              <p className="text-sm text-gray-500 mt-1">{currentStyle.description}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 缩放提示 */}
          <div className="px-6 pt-4">
            <ZoomIndicator zoomLevel={zoomLevel} onReset={(level: number) => setZoomLevel(level)} />
          </div>

          {/* 预览区域（支持滚轮缩放和滚动查看） */}
          <div
            ref={previewContainerRef}
            className="flex-1 overflow-auto preview-container"
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            {/* A4纸张预览 */}
            <div
              className="preview-paper mx-auto bg-white"
              style={{
                ...paperStyles,
                transform: `scale(${zoomLevel / 100})`,
                transition: 'transform 0.1s ease-out',
              }}
            >
              {/* 一级标题 */}
              <h1 style={previewStyles.heading1}>{SAMPLE_CONTENT.title}</h1>

              {/* 二级标题 */}
              <h2 style={previewStyles.heading2}>{SAMPLE_CONTENT.subtitle2}</h2>

              {/* 题目 */}
              {SAMPLE_CONTENT.questions.map((q) => (
                <div key={q.number}>
                  {/* 题号 + 题目文本 */}
                  <p style={previewStyles.questionNumber}>
                    {q.number}. {q.text}
                  </p>

                  {/* 选项 */}
                  <p style={previewStyles.option}>{q.options.join('  ')}</p>
                </div>
              ))}

              {/* 三级标题 */}
              <h3 style={previewStyles.heading3}>{SAMPLE_CONTENT.subtitle3}</h3>

              {/* 正文段落 */}
              <p style={previewStyles.body}>{SAMPLE_CONTENT.body}</p>
              <p style={previewStyles.body}>{SAMPLE_CONTENT.body2}</p>
            </div>
          </div>

          {/* 样式参数说明 */}
          <div className="p-3 border-t bg-white">
            {currentStyle.config && <StyleParameters style={currentStyle.config} />}
          </div>

          {/* 操作按钮 */}
          <div className="p-4 border-t bg-gray-50 flex space-x-3">
            <Button onClick={() => onApply(styleId)}>应用此样式</Button>
            <Button variant="outline" onClick={onClose}>
              关闭预览
            </Button>
          </div>
        </div>
      </div>

      <style>{`
        /* 预览容器样式 */
        .preview-container {
          /* 双向滚动 */
          overflow-x: auto;
          overflow-y: auto;

          /* 居中对齐 */
          display: flex;
          justify-content: center;

          /* 网格背景（辅助对齐） */
          background-color: #e5e5e5;
          background-image: linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
          background-size: 20px 20px;
        }

        /* A4纸张样式 */
        .preview-paper {
          /* 保持A4比例 */
          width: 210mm;
          min-height: 297mm;

          /* 字体渲染优化 */
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;

          /* 阴影效果（模拟纸张立体感） */
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -1px rgba(0, 0, 0, 0.06);

          /* 防止内容溢出 */
          overflow: hidden;

          /* 缩放原点：固定为中心 */
          transform-origin: center center;

          /* 快速响应 */
          transition: transform 0.1s ease-out;
        }
      `}</style>
    </>
  );
}
