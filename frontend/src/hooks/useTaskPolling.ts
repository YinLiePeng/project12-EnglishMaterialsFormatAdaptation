import { useEffect, useRef, useCallback } from 'react';
import { getTaskStatus } from '../services/api';
import type { TaskStatus } from '../types';

interface UseTaskPollingOptions {
  taskId: string | null;
  interval?: number;
  onSuccess?: (status: TaskStatus) => void;
  onError?: (error: Error) => void;
  onComplete?: (status: TaskStatus) => void;
}

export function useTaskPolling({
  taskId,
  interval = 2000,
  onSuccess,
  onError,
  onComplete,
}: UseTaskPollingOptions) {
  const timerRef = useRef<number | null>(null);
  const isPollingRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    isPollingRef.current = false;
  }, []);

  const poll = useCallback(async () => {
    if (!taskId || !isPollingRef.current) return;

    try {
      const status = await getTaskStatus(taskId);
      onSuccess?.(status);

      if (status.status === 'completed' || status.status === 'failed') {
        stopPolling();
        onComplete?.(status);
      }
    } catch (error) {
      onError?.(error as Error);
      stopPolling();
    }
  }, [taskId, onSuccess, onError, onComplete, stopPolling]);

  useEffect(() => {
    if (!taskId) {
      stopPolling();
      return;
    }

    isPollingRef.current = true;
    poll(); // 立即执行一次
    timerRef.current = window.setInterval(poll, interval);

    return () => {
      stopPolling();
    };
  }, [taskId, interval, poll, stopPolling]);

  return { stopPolling };
}
