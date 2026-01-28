/**
 * 定价管理筛选器组件
 * @description 提供关键词搜索、分类筛选、属性筛选等功能
 */
import React from 'react';

function PricingFilterBar({
  keyword,
  onKeywordChange,
  categoryId,
  onCategoryChange,
  mode,
  onModeChange,
  tokenTier,
  onTokenTierChange,
  supportsBatch,
  onSupportsBatchChange,
  supportsCache,
  onSupportsCacheChange,
  categories = [],
  filterOptions = {},
  onSearch,
  onReset,
  onAdd
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onSearch && onSearch();
    }
  };

  return (
    <div className="bg-white border border-border rounded-xl p-4 mb-6">
      <div className="flex flex-wrap items-center gap-3">
        {/* 搜索框 */}
        <div className="relative flex-1 min-w-[200px]">
          <input
            type="text"
            value={keyword}
            onChange={(e) => onKeywordChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索模型代码、名称..."
            className="w-full px-4 py-2 pl-10 border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
          />
          <svg className="w-4 h-4 text-text-secondary absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* 分类筛选 */}
        <select
          value={categoryId || ''}
          onChange={(e) => onCategoryChange(e.target.value ? parseInt(e.target.value) : null)}
          className="px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary bg-white min-w-[120px]"
        >
          <option value="">全部分类</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>

        {/* 模式筛选 */}
        <select
          value={mode || ''}
          onChange={(e) => onModeChange(e.target.value || null)}
          className="px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary bg-white min-w-[140px]"
        >
          <option value="">全部模式</option>
          {(filterOptions.modes || []).map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>

        {/* Token阶梯筛选 */}
        <select
          value={tokenTier || ''}
          onChange={(e) => onTokenTierChange(e.target.value || null)}
          className="px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary bg-white min-w-[140px]"
        >
          <option value="">全部Token阶梯</option>
          {(filterOptions.token_tiers || []).map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        {/* Batch支持 */}
        <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
          <input
            type="checkbox"
            checked={supportsBatch === true}
            onChange={(e) => onSupportsBatchChange(e.target.checked ? true : null)}
            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          />
          <span>Batch半价</span>
        </label>

        {/* Cache支持 */}
        <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
          <input
            type="checkbox"
            checked={supportsCache === true}
            onChange={(e) => onSupportsCacheChange(e.target.checked ? true : null)}
            className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
          />
          <span>缓存支持</span>
        </label>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={onReset}
            className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary border border-border rounded-lg hover:bg-secondary transition-colors"
          >
            重置
          </button>
          <button
            onClick={onSearch}
            className="px-4 py-2 text-sm text-white bg-primary rounded-lg hover:bg-opacity-90 transition-colors"
          >
            搜索
          </button>
          <button
            onClick={onAdd}
            className="px-4 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            新增模型
          </button>
        </div>
      </div>
    </div>
  );
}

export default PricingFilterBar;
