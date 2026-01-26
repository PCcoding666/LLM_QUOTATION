/**
 * 竞品分析弹窗组件
 * @description 显示Qwen模型与Doubao竞品的价格对比和销售话术
 */
import React, { useState, useEffect, useCallback } from 'react';
import { getCompetitorMatch, batchGetCompetitors } from '../../api';

/**
 * 高亮文本组件 - 安全地高亮关键词
 */
function HighlightText({ text, keywords = [] }) {
  if (!text || keywords.length === 0) {
    return <span>{text}</span>;
  }
  
  // 安全转义正则特殊字符
  const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = keywords.map(escapeRegex).join('|');
  const parts = text.split(new RegExp(`(${pattern})`, 'gi'));
  
  return (
    <>
      {parts.map((part, i) => {
        const isKeyword = keywords.some(kw => kw.toLowerCase() === part.toLowerCase());
        return isKeyword ? (
          <mark key={i} className="bg-yellow-200 text-yellow-800 px-1 rounded">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </>
  );
}

/**
 * 价格对比表格组件
 */
function PriceTable({ qwen, doubao, category }) {
  const isTextCategory = category === 'text';
  
  if (isTextCategory) {
    // 文本模型：输入/输出Token价格
    return (
      <div className="overflow-hidden rounded-lg border border-gray-200">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 w-20"></th>
              <th className="px-4 py-3 text-center text-xs font-medium text-blue-600">
                <div className="flex items-center justify-center gap-1">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  {qwen?.model || 'Qwen'}
                </div>
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 w-10">vs</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-orange-600">
                <div className="flex items-center justify-center gap-1">
                  <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                  {doubao?.model || 'Doubao'}
                </div>
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 w-16">对比</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="px-4 py-3 text-sm text-gray-600">输入</td>
              <td className="px-4 py-3 text-center">
                <span className="text-lg font-semibold text-blue-600">
                  {qwen?.input_price === 0 ? '免费' : `¥${qwen?.input_price || '-'}`}
                </span>
                {qwen?.input_price !== 0 && <span className="text-xs text-gray-400 ml-1">/M</span>}
              </td>
              <td className="px-4 py-3 text-center text-gray-300">=</td>
              <td className="px-4 py-3 text-center">
                <span className="text-lg font-semibold text-orange-600">
                  {doubao?.input_price === 0 ? '免费' : `¥${doubao?.input_price || '-'}`}
                </span>
                {doubao?.input_price !== 0 && <span className="text-xs text-gray-400 ml-1">/M</span>}
              </td>
              <td className="px-4 py-3 text-center">
                <CompareIndicator qwenPrice={qwen?.input_price} doubaoPrice={doubao?.input_price} />
              </td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm text-gray-600">输出</td>
              <td className="px-4 py-3 text-center">
                <span className="text-lg font-semibold text-blue-600">
                  {qwen?.output_price === 0 ? '免费' : `¥${qwen?.output_price || '-'}`}
                </span>
                {qwen?.output_price !== 0 && <span className="text-xs text-gray-400 ml-1">/M</span>}
              </td>
              <td className="px-4 py-3 text-center text-gray-300">=</td>
              <td className="px-4 py-3 text-center">
                <span className="text-lg font-semibold text-orange-600">
                  {doubao?.output_price === 0 ? '免费' : `¥${doubao?.output_price || '-'}`}
                </span>
                {doubao?.output_price !== 0 && <span className="text-xs text-gray-400 ml-1">/M</span>}
              </td>
              <td className="px-4 py-3 text-center">
                <CompareIndicator qwenPrice={qwen?.output_price} doubaoPrice={doubao?.output_price} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }
  
  // 图片/视频模型：单价
  const priceUnit = category === 'image' ? '/张' : '/秒';
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-center text-xs font-medium text-blue-600">
              <div className="flex items-center justify-center gap-1">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                {qwen?.model || 'Qwen'}
              </div>
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 w-10">vs</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-orange-600">
              <div className="flex items-center justify-center gap-1">
                <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                {doubao?.model || 'Doubao'}
              </div>
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 w-16">对比</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="px-4 py-4 text-center">
              <span className="text-xl font-semibold text-blue-600">¥{qwen?.unit_price || '-'}</span>
              <span className="text-xs text-gray-400 ml-1">{priceUnit}</span>
            </td>
            <td className="px-4 py-4 text-center text-gray-300">=</td>
            <td className="px-4 py-4 text-center">
              <span className="text-xl font-semibold text-orange-600">¥{doubao?.unit_price || '-'}</span>
              <span className="text-xs text-gray-400 ml-1">{priceUnit}</span>
            </td>
            <td className="px-4 py-4 text-center">
              <CompareIndicator qwenPrice={qwen?.unit_price} doubaoPrice={doubao?.unit_price} />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/**
 * 价格对比指示器
 */
function CompareIndicator({ qwenPrice, doubaoPrice }) {
  if (qwenPrice === null || doubaoPrice === null || qwenPrice === undefined || doubaoPrice === undefined) {
    return <span className="text-gray-400">-</span>;
  }
  
  if (qwenPrice === 0 && doubaoPrice > 0) {
    return <span className="text-green-500 font-medium text-sm">免费优势</span>;
  }
  
  if (qwenPrice < doubaoPrice) {
    const diff = ((doubaoPrice - qwenPrice) / doubaoPrice * 100).toFixed(0);
    return <span className="text-green-500 font-medium text-sm">-{diff}%</span>;
  } else if (qwenPrice > doubaoPrice) {
    const diff = ((qwenPrice - doubaoPrice) / doubaoPrice * 100).toFixed(0);
    return <span className="text-red-500 font-medium text-sm">+{diff}%</span>;
  }
  return <span className="text-gray-500 text-sm">相同</span>;
}

/**
 * 空状态组件
 */
function EmptyState({ modelName }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h4 className="text-lg font-medium text-gray-700 mb-2">该模型暂无竞品数据</h4>
      <p className="text-sm text-gray-500 max-w-xs">
        您可以继续完成报价流程，或联系产品团队补充竞品对标数据。
      </p>
    </div>
  );
}

/**
 * 竞品分析弹窗主组件
 */
export default function CompetitorModal({ isOpen, onClose, models = [] }) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [competitorData, setCompetitorData] = useState({});
  const [loading, setLoading] = useState(false);
  const [updateTime, setUpdateTime] = useState(null);
  
  // 提取关键词用于高亮
  const insightKeywords = ['上下文', '生态', '百炼', '性价比', '免费', '价格', '成本', '优势'];
  
  // 防止滚动穿透
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isOpen]);
  
  // 加载竞品数据
  useEffect(() => {
    if (isOpen && models.length > 0) {
      loadCompetitorData();
    }
  }, [isOpen, models]);
  
  const loadCompetitorData = async () => {
    setLoading(true);
    try {
      const modelCodes = models.map(m => m.model_code || m.id || m.name);
      const response = await batchGetCompetitors(modelCodes);
      
      if (response.data?.success) {
        setCompetitorData(response.data.results || {});
        setUpdateTime(response.data.update_time);
      }
    } catch (error) {
      console.error('加载竞品数据失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // 键盘导航
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(models.length - 1, prev + 1));
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, models.length, onClose]);
  
  if (!isOpen) return null;
  
  const currentModel = models[selectedIndex];
  const currentModelCode = currentModel?.model_code || currentModel?.id || currentModel?.name || '';
  const currentData = competitorData[currentModelCode];
  const hasCompetitor = currentData?.has_competitor;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* 弹窗内容 */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-[900px] max-h-[85vh] overflow-hidden flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">竞品对标分析</h3>
              <p className="text-xs text-gray-500">Qwen vs Doubao 价格与优势对比</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {updateTime && (
              <span className="text-xs text-gray-400">
                数据更新：{updateTime}
              </span>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
            >
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* 主体内容 - 左右分栏 */}
        <div className="flex flex-1 overflow-hidden">
          {/* 左侧模型列表 */}
          <div className="w-56 border-r border-gray-100 bg-gray-50/50 overflow-y-auto">
            <div className="p-3">
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2 px-2">
                报价单模型 ({models.length})
              </div>
              <div className="space-y-1">
                {models.map((model, index) => {
                  const modelCode = model.model_code || model.id || model.name;
                  const data = competitorData[modelCode];
                  const hasData = data?.has_competitor;
                  
                  return (
                    <button
                      key={modelCode}
                      onClick={() => setSelectedIndex(index)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-all ${
                        selectedIndex === index
                          ? 'bg-blue-500 text-white shadow-md'
                          : 'hover:bg-white text-gray-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate flex-1">
                          {model.model_code || model.name}
                        </span>
                        {hasData ? (
                          <span className={`w-2 h-2 rounded-full ${
                            selectedIndex === index ? 'bg-white' : 'bg-green-500'
                          }`} />
                        ) : (
                          <span className={`w-2 h-2 rounded-full ${
                            selectedIndex === index ? 'bg-white/50' : 'bg-gray-300'
                          }`} />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          
          {/* 右侧竞品详情 */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
                <span className="ml-3 text-gray-500">正在加载竞品数据...</span>
              </div>
            ) : hasCompetitor ? (
              <div className="space-y-6">
                {/* 模型信息头部 */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xl font-semibold text-gray-800">
                      {currentData.data.qwen?.model}
                    </h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                        {currentData.data.qwen?.role || '通义模型'}
                      </span>
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                        {currentData.data.category === 'text' ? '文本' : 
                         currentData.data.category === 'image' ? '图片' : '视频'}
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* 价格对比表格 */}
                <div>
                  <h5 className="text-sm font-medium text-gray-600 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    价格对比一览
                  </h5>
                  <PriceTable 
                    qwen={currentData.data.qwen}
                    doubao={currentData.data.doubao}
                    category={currentData.data.category}
                  />
                </div>
                
                {/* 竞争洞察话术 */}
                {currentData.data.insight && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-600 mb-3 flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      销售话术建议
                    </h5>
                    <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-100">
                      <p className="text-sm text-gray-700 leading-relaxed">
                        <HighlightText 
                          text={currentData.data.insight} 
                          keywords={insightKeywords}
                        />
                      </p>
                    </div>
                  </div>
                )}
                
                {/* 基线对比 */}
                {currentData.data.baseline?.model && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      <span>与国际基线 <strong>{currentData.data.baseline.model}</strong> 对比：</span>
                      <span className="text-green-600 font-medium">
                        {currentData.data.baseline.cost_ratio_vs_gemini || currentData.data.baseline.cost_ratio_vs_dalle || currentData.data.baseline.cost_ratio_vs_runway || currentData.data.baseline.cost_ratio_vs_mj}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState modelName={currentModelCode} />
            )}
          </div>
        </div>
        
        {/* 底部导航 */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50/50">
          <div className="text-sm text-gray-500">
            {selectedIndex + 1} / {models.length}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSelectedIndex(prev => Math.max(0, prev - 1))}
              disabled={selectedIndex === 0}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              上一个
            </button>
            <button
              onClick={() => setSelectedIndex(prev => Math.min(models.length - 1, prev + 1))}
              disabled={selectedIndex === models.length - 1}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
            >
              下一个
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <button
              onClick={onClose}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
