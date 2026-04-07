import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home } from './pages/Home';
import { Process } from './pages/Process';
import { Result } from './pages/Result';
import { TestCase } from './pages/TestCase';
import { TaskList } from './pages/TaskList';
import { TestCaseManagement } from './pages/TestCaseManagement';
import { DocumentPreview } from './pages/DocumentPreview';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ToastProvider } from './contexts/ToastContext';

const queryClient = new QueryClient();

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <div className="min-h-screen bg-gray-50">
              {/* 导航栏 */}
              <nav className="bg-white shadow-sm">
                <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
                  <Link to="/" className="text-lg font-semibold text-gray-900">
                    英语教学资料格式适配工具
                  </Link>
                  <div className="flex items-center space-x-4">
                    <Link
                      to="/tasks"
                      className="text-sm text-gray-600 hover:text-gray-900"
                    >
                      任务列表
                    </Link>
                    <Link
                      to="/testcases"
                      className="text-sm text-gray-600 hover:text-gray-900"
                    >
                      测试用例
                    </Link>
                    <Link
                      to="/feedback"
                      className="text-sm text-gray-600 hover:text-gray-900"
                    >
                      提交反馈
                    </Link>
                  </div>
                </div>
              </nav>

              {/* 路由内容 */}
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/tasks" element={<TaskList />} />
                <Route path="/testcases" element={<TestCaseManagement />} />
                <Route path="/process" element={<Process />} />
                <Route path="/result" element={<Result />} />
                <Route path="/feedback" element={<TestCase />} />
                <Route path="/preview/:taskId" element={<DocumentPreview />} />
              </Routes>
            </div>
          </BrowserRouter>
        </QueryClientProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
