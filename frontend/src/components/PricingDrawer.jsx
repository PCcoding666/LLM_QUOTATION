/**
 * 价格配置抽屉组件
 * @description 用于管理模型的价格维度（输入价格、输出价格等）
 */
import React, { useState, useEffect } from 'react';
import { getModelPricesAdmin, addModelPrice, updateModelPrice, deleteModelPrice } from '../api';

// 常用维度代码
const DIMENSION_OPTIONS = [
  { code: 'input', label: '输入', unit: '元/千Token' },
  { code: 'output', label: '输出', unit: '元/千Token' },
  { code: 'input_token', label: '输入Token', unit: '元/千Token' },
  { code: 'output_token', label: '输出Token', unit: '元/千Token' },
  { code: 'thinking_input', label: '思考输入', unit: '元/千Token' },
  { code: 'thinking_output', label: '思考输出', unit: '元/千Token' },
  { code: 'character', label: '字符', unit: '元/千字符' },
  { code: 'audio_second', label: '音频秒', unit: '元/秒' },
  { code: 'image_count', label: '图片数', unit: '元/张' },
  { code: 'video_second', label: '视频秒', unit: '元/秒' },
];

function PricingDrawer({ isOpen, onClose, model, onPriceChange }) {
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 新增价格表单
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPrice, setNewPrice] = useState({
    dimension_code: '',
    unit_price: '',
    unit: '元/千Token'
  });

  // 编辑状态
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');

  // 加载价格列表
  useEffect(() => {
    if (isOpen && model) {
      loadPrices();
    }
  }, [isOpen, model]);

  const loadPrices = async () => {
    if (!model) return;
    setLoading(true);
    try {
      const response = await getModelPricesAdmin(model.id);
      setPrices(response.data || []);
    } catch (error) {
      console.error('加载价格失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 添加价格
  const handleAddPrice = async () => {
    if (!newPrice.dimension_code || !newPrice.unit_price) {
      alert('请填写完整的价格信息');
      return;
    }

    setSaving(true);
    try {
      await addModelPrice(model.id, {
        dimension_code: newPrice.dimension_code,
        unit_price: parseFloat(newPrice.unit_price),
        unit: newPrice.unit
      });
      await loadPrices();
      setShowAddForm(false);
      setNewPrice({ dimension_code: '', unit_price: '', unit: '元/千Token' });
      onPriceChange && onPriceChange();
    } catch (error) {
      console.error('添加价格失败:', error);
      alert('添加价格失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 开始编辑
  const handleStartEdit = (price) => {
    setEditingId(price.id);
    setEditValue(price.unit_price.toString());
  };

  // 保存编辑
  const handleSaveEdit = async (priceId) => {
    if (!editValue) {
      setEditingId(null);
      return;
    }

    setSaving(true);
    try {
      await updateModelPrice(priceId, {
        unit_price: parseFloat(editValue)
      });
      await loadPrices();
      setEditingId(null);
      onPriceChange && onPriceChange();
    } catch (error) {
      console.error('更新价格失败:', error);
      alert('更新价格失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 删除价格
  const handleDeletePrice = async (priceId) => {
    if (!confirm('确定要删除这个价格维度吗？')) return;

    setSaving(true);
    try {
      await deleteModelPrice(priceId);
      await loadPrices();
      onPriceChange && onPriceChange();
    } catch (error) {
      console.error('删除价格失败:', error);
      alert('删除价格失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 获取维度显示名称
  const getDimensionLabel = (code) => {
    const option = DIMENSION_OPTIONS.find(d => d.code === code);
    return option ? option.label : code;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-end z-50">
      <div className="bg-white w-full max-w-lg h-full overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 bg-white border-b border-border p-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">价格配置</h2>
            {model && (
              <p className="text-sm text-text-secondary mt-1">
                {model.display_name} ({model.model_code})
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-secondary rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 模型信息 */}
        {model && (
          <div className="p-4 bg-secondary border-b border-border">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-text-secondary">分类：</span>
                <span className="text-text-primary">{model.category_name || '-'}</span>
              </div>
              <div>
                <span className="text-text-secondary">模式：</span>
                <span className="text-text-primary">{model.mode || '-'}</span>
              </div>
              <div>
                <span className="text-text-secondary">Token阶梯：</span>
                <span className="text-text-primary">{model.token_tier || '-'}</span>
              </div>
              <div>
                <span className="text-text-secondary">Batch：</span>
                <span className={model.supports_batch ? 'text-green-600' : 'text-text-secondary'}>
                  {model.supports_batch ? '支持' : '不支持'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 价格列表 */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-text-primary">价格维度</h3>
            <button
              onClick={() => setShowAddForm(true)}
              disabled={showAddForm}
              className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              添加维度
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8 text-text-secondary">加载中...</div>
          ) : (
            <div className="space-y-3">
              {/* 新增表单 */}
              {showAddForm && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="block text-xs text-text-secondary mb-1">维度</label>
                      <select
                        value={newPrice.dimension_code}
                        onChange={(e) => {
                          const option = DIMENSION_OPTIONS.find(d => d.code === e.target.value);
                          setNewPrice({
                            ...newPrice,
                            dimension_code: e.target.value,
                            unit: option?.unit || '元/千Token'
                          });
                        }}
                        className="w-full px-2 py-1.5 border border-border rounded text-sm focus:outline-none focus:border-primary bg-white"
                      >
                        <option value="">选择维度</option>
                        {DIMENSION_OPTIONS.map(d => (
                          <option key={d.code} value={d.code}>{d.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-text-secondary mb-1">单价</label>
                      <input
                        type="number"
                        step="0.000001"
                        value={newPrice.unit_price}
                        onChange={(e) => setNewPrice({ ...newPrice, unit_price: e.target.value })}
                        placeholder="0.000000"
                        className="w-full px-2 py-1.5 border border-border rounded text-sm focus:outline-none focus:border-primary"
                      />
                    </div>
                  </div>
                  <div className="mb-3">
                    <label className="block text-xs text-text-secondary mb-1">单位</label>
                    <input
                      type="text"
                      value={newPrice.unit}
                      onChange={(e) => setNewPrice({ ...newPrice, unit: e.target.value })}
                      className="w-full px-2 py-1.5 border border-border rounded text-sm focus:outline-none focus:border-primary"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setShowAddForm(false);
                        setNewPrice({ dimension_code: '', unit_price: '', unit: '元/千Token' });
                      }}
                      className="px-3 py-1.5 text-xs text-text-secondary border border-border rounded hover:bg-secondary transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleAddPrice}
                      disabled={saving}
                      className="px-3 py-1.5 text-xs text-white bg-primary rounded hover:bg-opacity-90 transition-colors disabled:opacity-50"
                    >
                      {saving ? '保存中...' : '添加'}
                    </button>
                  </div>
                </div>
              )}

              {/* 价格列表 */}
              {prices.length === 0 && !showAddForm ? (
                <div className="text-center py-8 text-text-secondary">
                  暂无价格配置，点击"添加维度"创建
                </div>
              ) : (
                prices.map(price => (
                  <div
                    key={price.id}
                    className="p-3 bg-white border border-border rounded-lg flex items-center justify-between"
                  >
                    <div className="flex-1">
                      <div className="text-sm font-medium text-text-primary">
                        {getDimensionLabel(price.dimension_code)}
                      </div>
                      <div className="text-xs text-text-secondary mt-0.5">
                        {price.dimension_code}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {editingId === price.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="0.000001"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-24 px-2 py-1 border border-primary rounded text-sm focus:outline-none"
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveEdit(price.id)}
                            disabled={saving}
                            className="text-green-600 hover:text-green-700"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="text-text-secondary hover:text-text-primary"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="text-sm font-medium text-primary">
                            {price.unit_price} {price.unit}
                          </span>
                          <button
                            onClick={() => handleStartEdit(price)}
                            className="p-1 text-text-secondary hover:text-primary transition-colors"
                            title="编辑"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDeletePrice(price.id)}
                            className="p-1 text-text-secondary hover:text-red-500 transition-colors"
                            title="删除"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PricingDrawer;
