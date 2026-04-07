import { create } from 'zustand';
import type { TaskStatus, TaskFilters, TaskSort, TaskStatistics } from '../types';
import { getTaskListAdvanced, getTaskStatistics, deleteTasksBatch } from '../services/api';

interface TaskListState {
  // 状态
  tasks: TaskStatus[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
  
  // 筛选和排序
  filters: TaskFilters;
  sort: TaskSort;
  activeFilters: TaskFilters;
  
  // 统计数据
  statistics: TaskStatistics | null;
  statisticsLoading: boolean;
  
  // 批量选择
  selectedTaskIds: Set<string>;
  
  // 操作
  fetchTasks: () => Promise<void>;
  fetchStatistics: () => Promise<void>;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setFilters: (filters: TaskFilters) => void;
  setSort: (sort: TaskSort) => void;
  resetFilters: () => void;
  toggleTaskSelection: (taskId: string) => void;
  selectAllTasks: () => void;
  clearSelection: () => void;
  deleteSelectedTasks: () => Promise<{ deleted_count: number; deleted_files: number }>;
  clearError: () => void;
}

const DEFAULT_FILTERS: TaskFilters = {};
const DEFAULT_SORT: TaskSort = { by: 'created_at', order: 'desc' };

export const useTaskStore = create<TaskListState>((set, get) => ({
  // 初始状态
  tasks: [],
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
  error: null,
  filters: DEFAULT_FILTERS,
  sort: DEFAULT_SORT,
  activeFilters: DEFAULT_FILTERS,
  statistics: null,
  statisticsLoading: false,
  selectedTaskIds: new Set<string>(),
  
  // 获取任务列表
  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const { page, pageSize, filters, sort } = get();
      const response = await getTaskListAdvanced({
        page,
        page_size: pageSize,
        filters,
        sort,
      });
      set({
        tasks: response.tasks,
        total: response.total,
        loading: false,
      });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      set({
        error: error.response?.data?.message || '获取任务列表失败',
        loading: false,
      });
    }
  },
  
  // 获取统计数据
  fetchStatistics: async () => {
    set({ statisticsLoading: true });
    try {
      const statistics = await getTaskStatistics();
      set({ statistics, statisticsLoading: false });
    } catch (err: unknown) {
      console.error('获取统计数据失败:', err);
      set({ statisticsLoading: false });
    }
  },
  
  // 设置页码
  setPage: (page: number) => {
    set({ page });
  },
  
  // 设置每页条数
  setPageSize: (pageSize: number) => {
    set({ pageSize, page: 1 });
  },
  
  // 设置筛选条件
  setFilters: (filters: TaskFilters) => {
    set({ filters, page: 1 });
  },
  
  // 设置排序
  setSort: (sort: TaskSort) => {
    set({ sort });
  },
  
  // 重置筛选
  resetFilters: () => {
    set({ filters: DEFAULT_FILTERS, page: 1 });
  },
  
  // 切换任务选择状态
  toggleTaskSelection: (taskId: string) => {
    const { selectedTaskIds } = get();
    const newSelection = new Set(selectedTaskIds);
    if (newSelection.has(taskId)) {
      newSelection.delete(taskId);
    } else {
      newSelection.add(taskId);
    }
    set({ selectedTaskIds: newSelection });
  },
  
  // 全选当前页
  selectAllTasks: () => {
    const { tasks } = get();
    const newSelection = new Set(tasks.map(task => task.task_id));
    set({ selectedTaskIds: newSelection });
  },
  
  // 清空选择
  clearSelection: () => {
    set({ selectedTaskIds: new Set<string>() });
  },
  
  // 批量删除选中的任务
  deleteSelectedTasks: async () => {
    const { selectedTaskIds } = get();
    if (selectedTaskIds.size === 0) {
      throw new Error('请先选择要删除的任务');
    }
    
    const taskIds = Array.from(selectedTaskIds);
    const result = await deleteTasksBatch(taskIds);
    
    // 清空选择并刷新列表
    set({ selectedTaskIds: new Set<string>() });
    await get().fetchTasks();
    await get().fetchStatistics();
    
    return result;
  },
  
  // 清除错误
  clearError: () => {
    set({ error: null });
  },
}));