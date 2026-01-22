/**
 * 步骤1 - 模型选择页面
 * @description 报价流程第一步：按分类浏览和选择要报价的模型
 * 设计原则：保持简单直观，只做模型选择，详细配置放在Step2
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPricingCategories, searchPricingModels } from '../api';

function QuoteStep1() {
  const navigate = useNavigate();
  
  // 分类树数据
  const [categoryTree, setCategoryTree] = useState([]);
  
  // 当前选中的分类
  const [activeCategory, setActiveCategory] = useState(null);
  
  // 搜索关键词
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  
  // 已选模型
  const [selectedModels, setSelectedModels] = useState([]);
  
  // 加载状态
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCategoryTree();
    restoreSavedData();
  }, []);

  /**
   * 加载分类模型树
   */
  const loadCategoryTree = async () => {
    setLoading(true);
    try {
      const response = await getPricingCategories();
      if (response.data && response.data.length > 0) {
        setCategoryTree(response.data);
        setActiveCategory(response.data[0].category_code);
      }
    } catch (error) {
      console.error('加载分类失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 恢复之前保存的数据
   */
  const restoreSavedData = () => {
    const step1Data = sessionStorage.getItem('quoteStep1');
    if (step1Data) {
      const { selectedModels: savedModels } = JSON.parse(step1Data);
      if (savedModels && savedModels.length > 0) {
        setSelectedModels(savedModels);
      }
    }
  };

  /**
   * 搜索模型
   */
  const handleSearch = async (keyword) => {
    setSearchKeyword(keyword);
    if (!keyword.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    
    setIsSearching(true);
    try {
      const response = await searchPricingModels(keyword, 30);
      setSearchResults(response.data || []);
    } catch (error) {
      console.error('搜索失败:', error);
      setSearchResults([]);
    }
  };

  /**
   * 获取当前分类的模型列表
   */
  const getCurrentModels = () => {
    if (isSearching && searchKeyword) {
      return searchResults;
    }
    const category = categoryTree.find(c => c.category_code === activeCategory);
    return category?.models || [];
  };

  /**
   * 切换模型选择状态
   */
  const handleToggleModel = (model) => {
    setSelectedModels(prev => {
      const exists = prev.find(m => m.model_code === model.model_code);
      if (exists) {
        return prev.filter(m => m.model_code !== model.model_code);
      } else {
        return [...prev, {
          model_code: model.model_code,
          model_name: model.model_name,
          display_name: model.model_code,  // 使用纯英文标识符
          category: model.category,  // 保存分类信息
          sub_category: model.sub_category  // 保存子分类信息
        }];
      }
    });
  };

  /**
   * 检查模型是否已选中
   */
  const isModelSelected = (modelCode) => {
    return selectedModels.some(m => m.model_code === modelCode);
  };

  /**
   * 移除已选模型
   */
  const handleRemoveModel = (modelCode) => {
    setSelectedModels(prev => prev.filter(m => m.model_code !== modelCode));
  };

  /**
   * 清空所有已选模型
   */
  const handleClearAll = () => {
    setSelectedModels([]);
  };

  /**
   * 检查当前分类是否已全选
   */
  const isCategoryAllSelected = () => {
    const currentModels = getCurrentModels();
    if (currentModels.length === 0) return false;
    return currentModels.every(m => isModelSelected(m.model_code));
  };

  /**
   * 全选当前分类
   */
  const handleSelectAll = () => {
    const currentModels = getCurrentModels();
    const newModels = currentModels.filter(m => !isModelSelected(m.model_code));
    setSelectedModels(prev => [...prev, ...newModels.map(m => ({
      model_code: m.model_code,
      model_name: m.model_name,
      display_name: m.model_code,  // 使用纯英文标识符
      category: m.category,  // 保存分类信息
      sub_category: m.sub_category  // 保存子分类信息
    }))]);
  };

  /**
   * 取消当前分类的全部选择
   */
  const handleDeselectAll = () => {
    const currentModels = getCurrentModels();
    const currentModelCodes = new Set(currentModels.map(m => m.model_code));
    setSelectedModels(prev => prev.filter(m => !currentModelCodes.has(m.model_code)));
  };

  /**
   * 下一步
   */
  const handleNext = () => {
    if (selectedModels.length === 0) {
      alert('请至少选择一个模型');
      return;
    }
    sessionStorage.setItem('quoteStep1', JSON.stringify({ selectedModels }));
    navigate('/quote/step2');
  };

  /**
   * 获取分类图标
   */
  const getCategoryIcon = (code) => {
    const icons = {
      'text_qwen': '💬',
      'text_qwen_opensource': '📝',
      'text_thirdparty': '🤖',
      'image_gen': '🎨',
      'image_gen_thirdparty': '🖼️',
      'tts': '🔊',
      'asr': '🎤',
      'video_gen': '🎬',
      'text_embedding': '📊',
      'multimodal_embedding': '🌐',
      'text_nlu': '🔍',
      'industry': '🏭'
    };
    return icons[code] || '📦';
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* 步骤进度条 */}
      <div className="flex items-center justify-center mb-8">
        <div className="flex items-center">
          <span className="text-primary font-medium">模型选择</span>
          <div className="w-24 h-px bg-border mx-4"></div>
          <span className="text-text-secondary">参数配置</span>
          <div className="w-24 h-px bg-border mx-4"></div>
          <span className="text-text-secondary">价格清单</span>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-text-secondary">加载中...</div>
      ) : (
        <div className="flex gap-6">
          {/* 左侧：分类导航 */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white border border-border rounded-xl p-4 sticky top-4">
              <h3 className="text-sm font-medium text-text-primary mb-3">模型分类</h3>
              <div className="space-y-1">
                {categoryTree.map(cat => (
                  <button
                    key={cat.category_code}
                    onClick={() => {
                      setActiveCategory(cat.category_code);
                      setSearchKeyword('');
                      setIsSearching(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all flex items-center justify-between ${
                      activeCategory === cat.category_code && !isSearching
                        ? 'bg-primary text-white'
                        : 'hover:bg-secondary text-text-primary'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span>{getCategoryIcon(cat.category_code)}</span>
                      <span className="truncate">{cat.category_name}</span>
                    </span>
                    <span className={`text-xs ${
                      activeCategory === cat.category_code && !isSearching
                        ? 'text-white/70'
                        : 'text-text-secondary'
                    }`}>
                      {cat.model_count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 右侧：模型列表 */}
          <div className="flex-1">
            <div className="bg-white border border-border rounded-xl p-6">
              {/* 搜索框 */}
              <div className="mb-4">
                <div className="relative">
                  <input
                    type="text"
                    value={searchKeyword}
                    onChange={(e) => handleSearch(e.target.value)}
                    placeholder="搜索模型名称..."
                    className="w-full px-4 py-2 pl-10 border border-border rounded-lg focus:outline-none focus:border-primary"
                  />
                  <svg className="w-5 h-5 text-text-secondary absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>

              {/* 当前分类标题 */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-text-primary">
                  {isSearching ? `搜索结果 (${searchResults.length})` : 
                    categoryTree.find(c => c.category_code === activeCategory)?.category_name || ''}
                </h3>
                {!isSearching && getCurrentModels().length > 0 && (
                  isCategoryAllSelected() ? (
                    <button
                      onClick={handleDeselectAll}
                      className="text-sm text-red-500 hover:text-red-600 flex items-center gap-1 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      取消全选
                    </button>
                  ) : (
                    <button
                      onClick={handleSelectAll}
                      className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      全选此分类
                    </button>
                  )
                )}
              </div>

              {/* 模型网格 */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
                {getCurrentModels().map(model => {
                  const selected = isModelSelected(model.model_code);
                  return (
                    <div
                      key={model.model_code}
                      onClick={() => handleToggleModel(model)}
                      className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                        selected
                          ? 'border-primary bg-blue-50'
                          : 'border-border hover:border-primary/50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-text-primary truncate">
                            {model.model_code || model.model_name}
                          </div>
                          <div className="text-xs text-text-secondary truncate mt-0.5">
                            {model.model_code}
                          </div>
                        </div>
                        {selected && (
                          <svg className="w-5 h-5 text-primary flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {getCurrentModels().length === 0 && (
                <div className="text-center py-8 text-text-secondary">
                  {isSearching ? '未找到匹配的模型' : '该分类暂无模型'}
                </div>
              )}
            </div>

            {/* 已选模型列表 */}
            <div className="bg-white border border-border rounded-xl p-6 mt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-text-primary">
                  已选模型
                  {selectedModels.length > 0 && (
                    <span className="ml-2 text-sm text-primary">({selectedModels.length}个)</span>
                  )}
                </h3>
                {selectedModels.length > 0 && (
                  <button
                    onClick={handleClearAll}
                    className="text-sm text-red-500 hover:text-red-600 flex items-center gap-1 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    清空全部
                  </button>
                )}
              </div>

              {selectedModels.length === 0 ? (
                <div className="text-center py-6 text-text-secondary">
                  请从左侧分类中选择模型
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedModels.map(model => (
                    <div
                      key={model.model_code}
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-primary rounded-full text-sm"
                    >
                      <span>{model.model_code || model.model_name}</span>
                      <button
                        onClick={() => handleRemoveModel(model.model_code)}
                        className="hover:text-red-500"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* 底部按钮 */}
              <div className="flex justify-end mt-6 pt-4 border-t border-border">
                <button
                  onClick={handleNext}
                  disabled={selectedModels.length === 0}
                  className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一步：配置参数
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default QuoteStep1;
