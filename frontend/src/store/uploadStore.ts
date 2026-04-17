import { create } from 'zustand';
import type { TaskStatus, MarkerPosition, TemplatePreviewResponse } from '../types';

interface UploadState {
  file: File | null;
  template: File | null;
  layoutMode: 'none' | 'empty' | 'complete';
  presetStyle: string;

  currentTaskId: string | null;
  taskStatus: TaskStatus | null;

  templatePreview: TemplatePreviewResponse | null;
  templatePreviewLoading: boolean;
  templatePreviewError: string | null;
  markerPosition: MarkerPosition | null;

  setFile: (file: File | null) => void;
  setTemplate: (template: File | null) => void;
  setLayoutMode: (mode: 'none' | 'empty' | 'complete') => void;
  setPresetStyle: (style: string) => void;
  setCurrentTaskId: (taskId: string | null) => void;
  setTaskStatus: (status: TaskStatus | null) => void;
  setTemplatePreview: (preview: TemplatePreviewResponse | null) => void;
  setTemplatePreviewLoading: (loading: boolean) => void;
  setTemplatePreviewError: (error: string | null) => void;
  setMarkerPosition: (pos: MarkerPosition | null) => void;
  reset: () => void;
}

const initialState = {
  file: null,
  template: null,
  layoutMode: 'none' as const,
  presetStyle: 'preserve',
  currentTaskId: null,
  taskStatus: null,
  templatePreview: null,
  templatePreviewLoading: false,
  templatePreviewError: null,
  markerPosition: null,
};

export const useUploadStore = create<UploadState>((set) => ({
  ...initialState,

  setFile: (file) => set({ file }),
  setTemplate: (template) => set({ template }),
  setLayoutMode: (mode) => set({ layoutMode: mode }),
  setPresetStyle: (style) => set({ presetStyle: style }),
  setCurrentTaskId: (taskId) => set({ currentTaskId: taskId }),
  setTaskStatus: (status) => set({ taskStatus: status }),
  setTemplatePreview: (preview) => set({ templatePreview: preview }),
  setTemplatePreviewLoading: (loading) => set({ templatePreviewLoading: loading }),
  setTemplatePreviewError: (error) => set({ templatePreviewError: error }),
  setMarkerPosition: (pos) => set({ markerPosition: pos }),

  reset: () => set(initialState),
}));
