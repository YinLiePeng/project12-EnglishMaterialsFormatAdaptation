import { useEffect, useState, useRef } from 'react';
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

function ZoomIndicator({
  zoomLevel,
  onReset,
}: {
  zoomLevel: number;
  onReset: (level: number) => void;
}) {
  return (
    <div className="flex items-center justify-between mb-4 px-4 py-2 bg-gray-50 rounded-lg">
      <div className="flex items-center space-x-2">
        <span className="text-sm font-medium text-gray-700">{zoomLevel}%</span>
        <span className="text-xs text-gray-400 hidden sm:inline">
          Ctrl +/-号缩放
        </span>
      </div>

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

function PreserveDrawerContent({ styleId, onApply, onClose }: {
  styleId: string;
  onApply: (styleId: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <h2 className="text-lg font-bold text-gray-900">保留原格式</h2>
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

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="font-medium text-green-900 mb-2">功能说明</h3>
          <p className="text-sm text-green-800 leading-relaxed">
            保持原文档全部格式不变，将内容复制到模板中。系统会自动审查并纠正复制过程中产生的格式漂移，确保输出文档与原文件格式一致。
          </p>
        </div>

        <div>
          <h3 className="font-medium text-gray-900 mb-3">保留的格式范围</h3>
          <div className="space-y-2">
            {[
              { icon: '📝', title: '文字格式', desc: '字体、字号、粗体、斜体、下划线、颜色' },
              { icon: '📏', title: '段落格式', desc: '缩进（首行/左/右）、行间距、段前段后间距、对齐方式' },
              { icon: '📊', title: '表格格式', desc: '列宽、行高、合并单元格、单元格边框、底色、垂直对齐' },
              { icon: '🖼️', title: '图片格式', desc: '原始尺寸、宽高比例' },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                <span className="text-lg">{item.icon}</span>
                <div>
                  <div className="font-medium text-gray-900 text-sm">{item.title}</div>
                  <div className="text-xs text-gray-500">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="font-medium text-gray-900 mb-3">格式审查</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            生成文档后，系统会自动比对原始格式与输出格式，检测并纠正因复制操作产生的格式漂移（如缩进偏移、字体变化、间距改变等）。仅纠正复制导致的差异，不修改原文件自身的不一致。
          </p>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-2">适用场景</h3>
          <ul className="text-sm text-gray-600 space-y-1.5">
            <li>• 需要将内容复制到学校统一的空模板中，但不想手动调整格式</li>
            <li>• 原文档格式已经很完善，不需要套用预设样式</li>
            <li>• 担心复制粘贴后格式走样（如缩进错误、字体变化）</li>
          </ul>
        </div>
      </div>

      <div className="p-4 border-t bg-gray-50 flex space-x-3">
        <Button variant="primary" onClick={() => onApply(styleId)} className="!bg-green-600 hover:!bg-green-700">
          应用此样式
        </Button>
        <Button variant="outline" onClick={onClose}>
          关闭
        </Button>
      </div>
    </div>
  );
}

function PreviewDrawerContent({ currentStyle, previewStyles, paperStyles, zoomLevel, setZoomLevel, styleId, onApply, onClose }: {
  currentStyle: PresetStyle;
  previewStyles: any;
  paperStyles: any;
  zoomLevel: number;
  setZoomLevel: (level: number) => void;
  styleId: string;
  onApply: (styleId: string) => void;
  onClose: () => void;
}) {
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const [touchDistance, setTouchDistance] = useState<number>(0);

  useEffect(() => {
    const container = previewContainerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -10 : 10;
      setZoomLevel(Math.min(200, Math.max(50, zoomLevel + delta)));
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => { container.removeEventListener('wheel', handleWheel); };
  }, [zoomLevel, setZoomLevel]);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      setTouchDistance(Math.sqrt(dx * dx + dy * dy));
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && touchDistance > 0) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const newDistance = Math.sqrt(dx * dx + dy * dy);
      const scale = newDistance / touchDistance;
      setZoomLevel(Math.min(200, Math.max(50, zoomLevel * scale)));
      setTouchDistance(newDistance);
    }
  };

  const handleTouchEnd = () => { setTouchDistance(0); };

  return (
    <div className="h-full flex flex-col">
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

      <div className="px-6 pt-4">
        <ZoomIndicator zoomLevel={zoomLevel} onReset={setZoomLevel} />
      </div>

      <div
        ref={previewContainerRef}
        className="flex-1 overflow-auto preview-container"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="preview-paper mx-auto bg-white"
          style={{
            ...paperStyles,
            transform: `scale(${zoomLevel / 100})`,
            transition: 'transform 0.1s ease-out',
          }}
        >
          <h1 style={previewStyles.heading1}>{SAMPLE_CONTENT.title}</h1>
          <h2 style={previewStyles.heading2}>{SAMPLE_CONTENT.subtitle2}</h2>
          {SAMPLE_CONTENT.questions.map((q) => (
            <div key={q.number}>
              <p style={previewStyles.questionNumber}>
                {q.number}. {q.text}
              </p>
              <p style={previewStyles.option}>{q.options.join('  ')}</p>
            </div>
          ))}
          <h3 style={previewStyles.heading3}>{SAMPLE_CONTENT.subtitle3}</h3>
          <p style={previewStyles.body}>{SAMPLE_CONTENT.body}</p>
          <p style={previewStyles.body}>{SAMPLE_CONTENT.body2}</p>
        </div>
      </div>

      <div className="p-3 border-t bg-white">
        {currentStyle.config && <StyleParameters style={currentStyle.config} />}
      </div>

      <div className="p-4 border-t bg-gray-50 flex space-x-3">
        <Button onClick={() => onApply(styleId)}>应用此样式</Button>
        <Button variant="outline" onClick={onClose}>
          关闭预览
        </Button>
      </div>

      <style>{`
        .preview-container {
          overflow-x: auto;
          overflow-y: auto;
          display: flex;
          justify-content: center;
          background-color: #e5e5e5;
          background-image: linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
          background-size: 20px 20px;
        }
        .preview-paper {
          width: 210mm;
          min-height: 297mm;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
          overflow: hidden;
          transform-origin: center center;
          transition: transform 0.1s ease-out;
        }
      `}</style>
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
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [isVisible, setIsVisible] = useState(false);
  const [shouldRender, setShouldRender] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
    }
  }, [isOpen]);

  useEffect(() => {
    if (shouldRender && isOpen) {
      const frame = requestAnimationFrame(() => {
        setIsVisible(true);
      });
      return () => cancelAnimationFrame(frame);
    }
    if (shouldRender && !isOpen) {
      setIsVisible(false);
      const timer = setTimeout(() => {
        setShouldRender(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [shouldRender, isOpen]);

  useEffect(() => {
    if (styleId && styles.length > 0) {
      const style = styles.find((s) => s.id === styleId);
      if (style) {
        setCurrentStyle(style);
        if (style.config && Object.keys(style.config).length > 0) {
          setPreviewStyles(generateStyleCSS(style.config));
          setPaperStyles(generatePaperStyles(style.config.page));
        } else {
          setPreviewStyles(null);
          setPaperStyles(null);
        }
      }
    }
  }, [styleId, styles]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        setZoomLevel((prev) => Math.min(200, prev + 10));
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault();
        setZoomLevel((prev) => Math.max(50, prev - 10));
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        setZoomLevel(100);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!shouldRender || !currentStyle) {
    return null;
  }

  const isPreserve = styleId === 'preserve';

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity duration-300 ${isVisible ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />

      <div className={`fixed inset-y-0 right-0 w-full ${isPreserve ? 'md:w-[500px]' : 'md:w-[600px] lg:w-[800px]'} bg-white shadow-xl z-50 transform transition-transform duration-300 ease-out ${isVisible ? 'translate-x-0' : 'translate-x-full'}`}>
        {isPreserve ? (
          <PreserveDrawerContent styleId={styleId} onApply={onApply} onClose={onClose} />
        ) : previewStyles && paperStyles ? (
          <PreviewDrawerContent
            currentStyle={currentStyle}
            previewStyles={previewStyles}
            paperStyles={paperStyles}
            zoomLevel={zoomLevel}
            setZoomLevel={setZoomLevel}
            styleId={styleId}
            onApply={onApply}
            onClose={onClose}
          />
        ) : null}
      </div>
    </>
  );
}
