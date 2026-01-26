/**
 * 报价上下文
 * @description 全局管理报价状态，支持AI助手和报价流程共享数据
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const QuoteContext = createContext(null);

/**
 * 报价状态管理 Provider
 */
export function QuoteProvider({ children }) {
  // 当前报价单中的项目
  const [quoteItems, setQuoteItems] = useState([]);
  
  // 客户信息
  const [customerInfo, setCustomerInfo] = useState({
    name: '',
    company: '',
    contact: '',
    email: ''
  });
  
  // 价格单位偏好：'thousand'（千Token）或 'million'（百万Token）
  const [priceUnit, setPriceUnit] = useState(() => {
    const saved = localStorage.getItem('priceUnitPreference');
    return saved || 'thousand';
  });
  
  // 切换价格单位
  const togglePriceUnit = useCallback(() => {
    setPriceUnit(prev => {
      const newUnit = prev === 'thousand' ? 'million' : 'thousand';
      localStorage.setItem('priceUnitPreference', newUnit);
      return newUnit;
    });
  }, []);

  // 初始化时从 sessionStorage 恢复数据
  useEffect(() => {
    try {
      const savedItems = sessionStorage.getItem('aiQuoteItems');
      if (savedItems) {
        setQuoteItems(JSON.parse(savedItems));
      }
    } catch (e) {
      console.error('Failed to load quote items from session:', e);
    }
  }, []);

  // 当 quoteItems 变化时保存到 sessionStorage
  useEffect(() => {
    sessionStorage.setItem('aiQuoteItems', JSON.stringify(quoteItems));
  }, [quoteItems]);

  /**
   * 添加报价项
   * @param {Object} item - 报价项数据（来自AI生成的quote_item）
   */
  const addQuoteItem = useCallback((item) => {
    if (!item) return false;
    
    setQuoteItems(prev => {
      // 检查是否已存在相同配置的报价项
      const existingIndex = prev.findIndex(
        i => i.model_name === item.model_name && 
             i.config?.daily_calls === item.config?.daily_calls
      );
      
      if (existingIndex >= 0) {
        // 更新已存在的项目
        const updated = [...prev];
        updated[existingIndex] = { ...item, id: prev[existingIndex].id };
        return updated;
      }
      
      // 添加新项目
      return [...prev, { ...item, id: item.id || `qi_${Date.now()}` }];
    });
    
    return true;
  }, []);

  /**
   * 移除报价项
   * @param {string} itemId - 报价项ID
   */
  const removeQuoteItem = useCallback((itemId) => {
    setQuoteItems(prev => prev.filter(item => item.id !== itemId));
  }, []);

  /**
   * 更新报价项
   * @param {string} itemId - 报价项ID
   * @param {Object} updates - 更新的字段
   */
  const updateQuoteItem = useCallback((itemId, updates) => {
    setQuoteItems(prev => prev.map(item => 
      item.id === itemId ? { ...item, ...updates } : item
    ));
  }, []);

  /**
   * 清空报价单
   */
  const clearQuote = useCallback(() => {
    setQuoteItems([]);
    sessionStorage.removeItem('aiQuoteItems');
  }, []);

  /**
   * 计算报价总计
   */
  const getQuoteSummary = useCallback(() => {
    const totalMonthly = quoteItems.reduce((sum, item) => sum + (item.monthly_cost || 0), 0);
    const totalCost = quoteItems.reduce((sum, item) => sum + (item.total_cost || 0), 0);
    
    return {
      itemCount: quoteItems.length,
      totalMonthly,
      totalCost,
      items: quoteItems
    };
  }, [quoteItems]);

  /**
   * 将AI报价同步到传统报价流程
   * 用于将AI助手生成的报价项转换为传统报价流程所需的格式
   */
  const syncToTraditionalFlow = useCallback(() => {
    // 转换为 Step1 格式
    const step1Models = quoteItems.map((item, index) => ({
      id: index + 1,
      name: item.model_name,
      region: '中国大陆',
      brand: '通义千问',
      category: item.category?.split('-').pop() || '文本',
      group: '通用文本模型'
    }));
    
    sessionStorage.setItem('quoteStep1', JSON.stringify({
      selectedModels: step1Models
    }));
    
    // 转换为 Step2 格式
    const step2Configs = {};
    quoteItems.forEach((item, index) => {
      step2Configs[index + 1] = [{
        model_id: item.model_id,
        spec_name: item.model_name,
        daily_calls: item.config?.daily_calls || 1000,
        input_price: item.pricing?.input_price || 0,
        output_price: item.pricing?.output_price || 0,
        monthly_cost: item.monthly_cost
      }];
    });
    
    sessionStorage.setItem('quoteStep2', JSON.stringify({
      selectedModels: step1Models,
      modelConfigs: step2Configs
    }));
    
    return true;
  }, [quoteItems]);

  const value = {
    quoteItems,
    customerInfo,
    setCustomerInfo,
    addQuoteItem,
    removeQuoteItem,
    updateQuoteItem,
    clearQuote,
    getQuoteSummary,
    syncToTraditionalFlow,
    priceUnit,
    togglePriceUnit
  };

  return (
    <QuoteContext.Provider value={value}>
      {children}
    </QuoteContext.Provider>
  );
}

/**
 * 使用报价上下文的 Hook
 */
export function useQuote() {
  const context = useContext(QuoteContext);
  if (!context) {
    throw new Error('useQuote must be used within a QuoteProvider');
  }
  return context;
}

export default QuoteContext;
