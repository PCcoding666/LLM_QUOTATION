/**
 * 模型规格与价格管理页面
 * @description 提供模型定价数据的 CRUD 管理功能
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  getPricingModelsAdmin,
  getPricingCategoriesAdmin,
  getPricingFiltersAdmin,
  createPricingModel,
  updatePricingModel,
  deletePricingModel,
  batchDeletePricingModels
} from '../api';
import PricingFilterBar from '../components/PricingFilterBar';
import PricingModelModal from '../components/PricingModelModal';
import PricingDrawer from '../components/PricingDrawer';

function PricingManagement() {
  // 数据状态
  const [models, setModels] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 筛选状态
  const [keyword, setKeyword] = useState('');
  const [categoryId, setCategoryId] = useState(null);
  const [mode, setMode] = useState(null);
  const [tokenTier, setTokenTier] = useState(null);
  const [supportsBatch, setSupportsBatch] = useState(null);
  const [supportsCache, setSupportsCache] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // 选中状态
  const [selectedIds, setSelectedIds] = useState([]);

  // 弹窗状态
  const [showModal, setShowModal] = useState(false);
  const [editingModel, setEditingModel] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);

  // 抽屉状态
  const [showDrawer, setShowDrawer] = useState(false);
  const [drawerModel, setDrawerModel] = useState(null);

  // 初始化加载
  useEffect(() => {
    loadCategories();
    loadFilterOptions();
  }, []);

  // 加载模型列表
  useEffect(() => {
    loadModels();
  }, [page, categoryId, mode, tokenTier, supportsBatch, supportsCache]);

  // 加载分类列表
  const loadCategories = async () => {
    try {
      const response = await getPricingCategoriesAdmin();
      setCategories(response.data || []);
    } catch (error) {
      console.error('加载分类失败:', error);
    }
  };

  // 加载筛选选项
  const loadFilterOptions = async () => {
    try {
      const response = await getPricingFiltersAdmin();
      setFilterOptions(response.data || {});
    } catch (error) {
      console.error('加载筛选选项失败:', error);
    }
  };

  // 加载模型列表
  const loadModels = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        category_id: categoryId || undefined,
        mode: mode || undefined,
        token_tier: tokenTier || undefined,
        supports_batch: supportsBatch,
        supports_cache: supportsCache,
        status: 'active'
      };
      const response = await getPricingModelsAdmin(params);
      setModels(response.data?.data || []);
      setTotal(response.data?.total || 0);
    } catch (error) {
      console.error('加载模型列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword, categoryId, mode, tokenTier, supportsBatch, supportsCache]);

  // 搜索
  const handleSearch = () => {
    setPage(1);
    loadModels();
  };

  // 重置筛选
  const handleReset = () => {
    setKeyword('');
    setCategoryId(null);
    setMode(null);
    setTokenTier(null);
    setSupportsBatch(null);
    setSupportsCache(null);
    setPage(1);
  };

  // 打开新增弹窗
  const handleAdd = () => {
    setEditingModel(null);
    setShowModal(true);
  };

  // 打开编辑弹窗
  const handleEdit = (model) => {
    setEditingModel(model);
    setShowModal(true);
  };

  // 提交模型表单
  const handleSubmitModel = async (data) => {
    setModalLoading(true);
    try {
      if (editingModel) {
        await updatePricingModel(editingModel.id, data);
      } else {
        await createPricingModel(data);
      }
      setShowModal(false);
      setEditingModel(null);
      loadModels();
    } catch (error) {
      console.error('保存模型失败:', error);
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setModalLoading(false);
    }
  };

  // 删除模型
  const handleDelete = async (model) => {
    if (!confirm(`确定要删除模型 "${model.display_name}" 吗？`)) return;

    try {
      await deletePricingModel(model.id);
      loadModels();
    } catch (error) {
      console.error('删除模型失败:', error);
      alert('删除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) {
      alert('请先选择要删除的模型');
      return;
    }
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个模型吗？`)) return;

    try {
      await batchDeletePricingModels(selectedIds);
      setSelectedIds([]);
      loadModels();
    } catch (error) {
      console.error('批量删除失败:', error);
      alert('批量删除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 打开价格配置抽屉
  const handleConfigPrice = (model) => {
    setDrawerModel(model);
    setShowDrawer(true);
  };

  // 全选/取消全选
  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(models.map(m => m.id));
    } else {
      setSelectedIds([]);
    }
  };

  // 单选
  const handleSelectOne = (id, checked) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id]);
    } else {
      setSelectedIds(prev => prev.filter(i => i !== id));
    }
  };

  // 获取价格显示
  const getPriceDisplay = (prices) => {
    if (!prices || prices.length === 0) return '-';
    const input = prices.find(p => p.dimension_code === 'input' || p.dimension_code === 'input_token');
    const output = prices.find(p => p.dimension_code === 'output' || p.dimension_code === 'output_token');
    if (input && output) {
      return `${input.unit_price}/${output.unit_price}`;
    }
    return prices[0]?.unit_price || '-';
  };

  // 分页
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="max-w-7xl mx-auto">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">模型规格与价格管理</h1>
        <p className="text-sm text-text-secondary mt-1">
          管理大模型的规格参数和定价信息，修改后将实时同步到报价流程
        </p>
      </div>

      {/* 筛选器 */}
      <PricingFilterBar
        keyword={keyword}
        onKeywordChange={setKeyword}
        categoryId={categoryId}
        onCategoryChange={setCategoryId}
        mode={mode}
        onModeChange={setMode}
        tokenTier={tokenTier}
        onTokenTierChange={setTokenTier}
        supportsBatch={supportsBatch}
        onSupportsBatchChange={setSupportsBatch}
        supportsCache={supportsCache}
        onSupportsCacheChange={setSupportsCache}
        categories={categories}
        filterOptions={filterOptions}
        onSearch={handleSearch}
        onReset={handleReset}
        onAdd={handleAdd}
      />

      {/* 批量操作栏 */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-4 flex items-center justify-between">
          <span className="text-sm text-blue-800">
            已选择 {selectedIds.length} 个模型
          </span>
          <button
            onClick={handleBatchDelete}
            className="px-3 py-1.5 text-sm text-white bg-red-500 rounded hover:bg-red-600 transition-colors"
          >
            批量删除
          </button>
        </div>
      )}

      {/* 数据表格 */}
      <div className="bg-white border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-secondary">
              <tr>
                <th className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === models.length && models.length > 0}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-text-primary">模型代码</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-text-primary">显示名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-text-primary">分类</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-text-primary">模式</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-text-primary">Token阶梯</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-text-primary">价格(输入/输出)</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-text-primary">特性</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-text-primary">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-text-secondary">
                    加载中...
                  </td>
                </tr>
              ) : models.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-text-secondary">
                    暂无数据
                  </td>
                </tr>
              ) : (
                models.map(model => (
                  <tr key={model.id} className="hover:bg-secondary/50 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(model.id)}
                        onChange={(e) => handleSelectOne(model.id, e.target.checked)}
                        className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-text-primary">{model.model_code}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-text-primary">{model.display_name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-text-secondary">{model.category_name || '-'}</span>
                    </td>
                    <td className="px-4 py-3">
                      {model.mode ? (
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">
                          {model.mode}
                        </span>
                      ) : (
                        <span className="text-text-secondary text-sm">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {model.token_tier ? (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                          {model.token_tier}
                        </span>
                      ) : (
                        <span className="text-text-secondary text-sm">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm font-medium text-primary">
                        {getPriceDisplay(model.prices)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {model.supports_batch && (
                          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded" title="支持Batch半价">
                            B
                          </span>
                        )}
                        {model.supports_cache && (
                          <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 text-xs rounded" title="支持上下文缓存">
                            C
                          </span>
                        )}
                        {!model.supports_batch && !model.supports_cache && (
                          <span className="text-text-secondary text-sm">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleConfigPrice(model)}
                          className="p-1.5 text-text-secondary hover:text-primary hover:bg-secondary rounded transition-colors"
                          title="配置价格"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleEdit(model)}
                          className="p-1.5 text-text-secondary hover:text-primary hover:bg-secondary rounded transition-colors"
                          title="编辑"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDelete(model)}
                          className="p-1.5 text-text-secondary hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="删除"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-border flex items-center justify-between">
            <span className="text-sm text-text-secondary">
              共 {total} 条记录，第 {page}/{totalPages} 页
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm border border-border rounded hover:bg-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 text-sm border border-border rounded hover:bg-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 新增/编辑弹窗 */}
      <PricingModelModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setEditingModel(null);
        }}
        onSubmit={handleSubmitModel}
        model={editingModel}
        categories={categories}
        filterOptions={filterOptions}
        loading={modalLoading}
      />

      {/* 价格配置抽屉 */}
      <PricingDrawer
        isOpen={showDrawer}
        onClose={() => {
          setShowDrawer(false);
          setDrawerModel(null);
        }}
        model={drawerModel}
        onPriceChange={loadModels}
      />
    </div>
  );
}

export default PricingManagement;
