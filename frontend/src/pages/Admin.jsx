import React, { useState, useEffect, useCallback } from 'react';

/**
 * 管理员页面
 * 提供价格数据同步等管理功能
 */
function Admin() {
  const [syncStatus, setSyncStatus] = useState({
    is_running: false,
    current_step: '',
    progress: 0,
    last_result: null,
    last_run_time: null,
    error: null
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // 获取同步状态
  const fetchSyncStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/admin/sync-status');
      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
      }
    } catch (error) {
      console.error('获取同步状态失败:', error);
    }
  }, []);

  // 定时轮询状态（当任务运行时）
  useEffect(() => {
    fetchSyncStatus();
    
    let interval;
    if (syncStatus.is_running) {
      interval = setInterval(fetchSyncStatus, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [syncStatus.is_running, fetchSyncStatus]);

  // 触发同步任务
  const handleSync = async () => {
    if (syncStatus.is_running) {
      setMessage({ type: 'warning', text: '同步任务正在执行中，请稍候...' });
      return;
    }

    setIsLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await fetch('/api/v1/admin/sync-pricing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: '同步任务已启动，请等待完成...' });
        // 立即刷新状态
        setTimeout(fetchSyncStatus, 500);
      } else {
        setMessage({ type: 'error', text: data.detail || '启动同步任务失败' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误: ' + error.message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">系统管理</h1>

      {/* 价格数据同步卡片 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          价格数据同步
        </h2>
        
        <p className="text-gray-600 mb-4">
          一键同步最新的模型价格数据，包括解析、校验和更新数据库。
        </p>

        {/* 消息提示 */}
        {message.text && (
          <div className={`mb-4 p-3 rounded-lg ${
            message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
            message.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
            'bg-yellow-50 text-yellow-700 border border-yellow-200'
          }`}>
            {message.text}
          </div>
        )}

        {/* 同步状态 */}
        {syncStatus.is_running && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="font-medium text-blue-700">正在执行同步...</span>
            </div>
            <p className="text-blue-600 text-sm mb-2">{syncStatus.current_step}</p>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${syncStatus.progress}%` }}
              ></div>
            </div>
            <p className="text-blue-600 text-xs mt-1">{syncStatus.progress}%</p>
          </div>
        )}

        {/* 上次同步结果 */}
        {syncStatus.last_result && !syncStatus.is_running && (
          <div className={`mb-4 p-4 rounded-lg border ${
            syncStatus.last_result.success 
              ? 'bg-green-50 border-green-200' 
              : 'bg-red-50 border-red-200'
          }`}>
            <h4 className={`font-medium mb-1 ${
              syncStatus.last_result.success ? 'text-green-700' : 'text-red-700'
            }`}>
              上次同步: {syncStatus.last_result.success ? '成功' : '失败'}
            </h4>
            <p className="text-sm text-gray-600">
              时间: {syncStatus.last_run_time ? new Date(syncStatus.last_run_time).toLocaleString() : '未知'}
            </p>
            {syncStatus.last_result.updated_records !== undefined && (
              <p className="text-sm text-gray-600">
                更新记录数: {syncStatus.last_result.updated_records}
              </p>
            )}
            {syncStatus.error && (
              <p className="text-sm text-red-600 mt-1">错误: {syncStatus.error}</p>
            )}
          </div>
        )}

        {/* 同步按钮 */}
        <button
          onClick={handleSync}
          disabled={isLoading || syncStatus.is_running}
          className={`px-6 py-3 rounded-lg font-medium text-white transition-all flex items-center gap-2 ${
            isLoading || syncStatus.is_running
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
          }`}
        >
          {(isLoading || syncStatus.is_running) ? (
            <>
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              同步中...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              一键同步价格数据
            </>
          )}
        </button>
      </div>

      {/* 说明卡片 */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
        <h3 className="font-medium text-gray-800 mb-3">同步说明</h3>
        <ul className="text-sm text-gray-600 space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-blue-500 mt-0.5">1.</span>
            <span>解析最新的价格数据源文件</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-500 mt-0.5">2.</span>
            <span>自动校验并更新价格数据</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-500 mt-0.5">3.</span>
            <span>更新数据库中的价格记录</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Admin;
