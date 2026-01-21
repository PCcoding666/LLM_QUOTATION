import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import SelectCategory from './pages/SelectCategory';
import SelectModel from './pages/SelectModel';
import Configure from './pages/Configure';
import QuoteStep1 from './pages/QuoteStep1';
import QuoteStep2 from './pages/QuoteStep2';
import QuoteStep3 from './pages/QuoteStep3';
import QuoteHistory from './pages/QuoteHistory';
import DebatePage from './pages/DebatePage';
import Admin from './pages/Admin';
import ChatWindow from './components/ChatWindow';
import { QuoteProvider } from './context/QuoteContext';

/**
 * 应用主组件
 * @description 管理全局布局和路由，集成AI报价助手
 */
function App() {
  const location = useLocation();
  const [isChatOpen, setIsChatOpen] = useState(false);
  
  // 首页采用全局布局
  const isHomePage = location.pathname === '/';

  // 监听打开 AI 助手的事件（来自首页按钮）
  useEffect(() => {
    const handleOpenAI = () => setIsChatOpen(true);
    window.addEventListener('openAIAssistant', handleOpenAI);
    return () => window.removeEventListener('openAIAssistant', handleOpenAI);
  }, []);

  return (
    <QuoteProvider>
    <div className="min-h-screen bg-white">
      {/* 首页无导航栏，内页显示简洁头部 */}
      {!isHomePage && (
        <header className="bg-white border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center">
            <Link 
              to="/" 
              className="text-lg font-semibold text-text-primary hover:text-primary transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              报价侠
            </Link>
          </div>
        </header>
      )}

      {/* 主内容区 */}
      {isHomePage ? (
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
          </Routes>
        </main>
      ) : (
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/select-category" element={<SelectCategory />} />
            <Route path="/select-model/:categoryCode" element={<SelectModel />} />
            <Route path="/configure/:modelId" element={<Configure />} />
            <Route path="/quote/step1" element={<QuoteStep1 />} />
            <Route path="/quote/step2" element={<QuoteStep2 />} />
            <Route path="/quote/step3" element={<QuoteStep3 />} />
            <Route path="/quote-history" element={<QuoteHistory />} />
            <Route path="/debate" element={<DebatePage />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </main>
      )}

      {/* AI 智能报价助手悬浮按钮 - 全局可用 */}
      <button
          onClick={() => setIsChatOpen(!isChatOpen)}
          className={`fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all z-50 ${
            isChatOpen 
              ? 'bg-gray-600 hover:bg-gray-700' 
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700'
          }`}
          title="AI 报价助手"
        >
          {isChatOpen ? (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          )}
        </button>

      {/* AI 报价助手窗口 */}
      <ChatWindow isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
    </QuoteProvider>
  );
}

export default App;
