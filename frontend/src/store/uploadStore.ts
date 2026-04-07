import { create } from 'zustand';
import type { TaskStatus } from '../types';

interface UploadState {
  // 上传状态
  file: File | null;
  template: File | null;
  layoutMode: 'none' | 'empty' | 'complete';
  presetStyle: string;

  // 任务状态
  currentTaskId: string | null;
  taskStatus: TaskStatus | null;

  // Actions
  setFile: (file: File | null) => void;
  setTemplate: (template: File | null) => void;
  setLayoutMode: (mode: 'none' | 'empty' | 'complete') => void;
  setPresetStyle: (style: string) => void;
  setCurrentTaskId: (taskId: string | null) => void;
  setTaskStatus: (status: TaskStatus | null) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  // 初始状态
  file: null,
  template: null,
  layoutMode: 'none',
  presetStyle: 'universal',  // 默认使用通用排版

  currentTaskId: null,
  taskStatus: null,

  // Actions
  setFile: (file) => set({ file }),
  setTemplate: (template) => set({ template }),
  setLayoutMode: (mode) => set({ layoutMode: mode }),
  setPresetStyle: (style) => set({ presetStyle: style }),
  setCurrentTaskId: (taskId) => set({ currentTaskId: taskId }),
  setTaskStatus: (status) => set({ taskStatus: status }),

  reset: () => set({
    file: null,
    template: null,
    layoutMode: 'none',
    presetStyle: 'universal',
    currentTaskId: null,
    taskStatus: null,
  }),
}));
