import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Home } from './pages/Home';
import { Process } from './pages/Process';
import { TestCase } from './pages/TestCase';
import { TaskList } from './pages/TaskList';
import { TestCaseManagement } from './pages/TestCaseManagement';
import { DocumentPreview } from './pages/DocumentPreview';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ToastProvider } from './contexts/ToastContext';

const queryClient = new QueryClient();

const NAV_LINKS = [
  { to: '/tasks', label: '任务列表' },
  { to: '/feedback', label: '提交反馈' },
];

const ADMIN_LINKS = [
  { to: '/testcases', label: '测试用例管理' },
];

function NavLinks({ links = NAV_LINKS, onClick }: { links?: { to: string; label: string }[]; onClick?: () => void }) {
  const location = useLocation();
  return (
    <>
      {links.map((link) => {
        const isActive = location.pathname === link.to;
        return (
          <Link
            key={link.to}
            to={link.to}
            onClick={onClick}
            className={`text-sm transition-colors ${
              isActive
                ? 'text-blue-600 font-medium'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </>
  );
}

function AppContent() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center justify-between">
          <Link to="/" className="flex flex-col">
            <span className="text-base font-semibold text-gray-900">英语教学资料格式适配工具</span>
            <span className="text-xs text-gray-400">一站式解决教学资料的智能清洗、格式迁移适配、分级内容纠错</span>
          </Link>
          <div className="hidden md:flex items-center space-x-4">
            <NavLinks />
            {import.meta.env.DEV && (
              <>
                <span className="text-gray-200">|</span>
                <NavLinks links={ADMIN_LINKS} />
              </>
            )}
          </div>
          <button
            className="md:hidden p-2 text-gray-600 hover:text-gray-900"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-100 px-4 py-3 space-y-3">
            <NavLinks onClick={() => setMobileMenuOpen(false)} />
            {import.meta.env.DEV && (
              <>
                <div className="border-t border-gray-100 my-2" />
                <NavLinks links={ADMIN_LINKS} onClick={() => setMobileMenuOpen(false)} />
              </>
            )}
          </div>
        )}
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tasks" element={<TaskList />} />
        <Route path="/testcases" element={<TestCaseManagement />} />
        <Route path="/process" element={<Process />} />
        <Route path="/feedback" element={<TestCase />} />
        <Route path="/preview/:taskId" element={<DocumentPreview />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </QueryClientProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
