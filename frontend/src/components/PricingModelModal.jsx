/**
 * 定价模型新增/编辑弹窗组件
 * @description 用于创建或编辑模型规格信息
 */
import React, { useState, useEffect } from 'react';

function PricingModelModal({
  isOpen,
  onClose,
  onSubmit,
  model = null,
  categories = [],
  filterOptions = {},
  loading = false
}) {
  const isEdit = !!model;

  // 表单数据
  const [formData, setFormData] = useState({
    category_id: '',
    model_code: '',
    model_name: '',
    display_name: '',
    mode: '',
    token_tier: '',
    resolution: '',
    supports_batch: false,
    supports_cache: false,
    remark: ''
  });

  // 表单错误
  const [errors, setErrors] = useState({});

  // 初始化表单数据
  useEffect(() => {
    if (model) {
      setFormData({
        category_id: model.category_id || '',
        model_code: model.model_code || '',
        model_name: model.model_name || '',
        display_name: model.display_name || '',
        mode: model.mode || '',
        token_tier: model.token_tier || '',
        resolution: model.resolution || '',
        supports_batch: model.supports_batch || false,
        supports_cache: model.supports_cache || false,
        remark: model.remark || ''
      });
    } else {
      setFormData({
        category_id: '',
        model_code: '',
        model_name: '',
        display_name: '',
        mode: '',
        token_tier: '',
        resolution: '',
        supports_batch: false,
        supports_cache: false,
        remark: ''
      });
    }
    setErrors({});
  }, [model, isOpen]);

  // 处理输入变化
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // 清除该字段的错误
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  // 表单验证
  const validate = () => {
    const newErrors = {};

    if (!formData.category_id) {
      newErrors.category_id = '请选择分类';
    }
    if (!formData.model_code.trim()) {
      newErrors.model_code = '请输入模型代码';
    }
    if (!formData.model_name.trim()) {
      newErrors.model_name = '请输入模型名称';
    }
    if (!formData.display_name.trim()) {
      newErrors.display_name = '请输入显示名称';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 提交表单
  const handleSubmit = () => {
    if (!validate()) return;

    const submitData = {
      ...formData,
      category_id: parseInt(formData.category_id),
      mode: formData.mode || null,
      token_tier: formData.token_tier || null,
      resolution: formData.resolution || null,
      remark: formData.remark || null
    };

    onSubmit(submitData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-text-primary">
            {isEdit ? '编辑模型' : '新增模型'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-secondary rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 表单内容 */}
        <div className="p-6 space-y-6">
          {/* 基础信息 */}
          <div>
            <h3 className="text-sm font-medium text-text-primary mb-4">基础信息</h3>
            <div className="grid grid-cols-2 gap-4">
              {/* 分类 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  分类 <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.category_id}
                  onChange={(e) => handleChange('category_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:border-primary bg-white ${
                    errors.category_id ? 'border-red-500' : 'border-border'
                  }`}
                >
                  <option value="">请选择分类</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
                {errors.category_id && (
                  <p className="text-xs text-red-500 mt-1">{errors.category_id}</p>
                )}
              </div>

              {/* 模型代码 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  模型代码 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.model_code}
                  onChange={(e) => handleChange('model_code', e.target.value)}
                  disabled={isEdit}
                  placeholder="如：qwen3-max"
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:border-primary ${
                    errors.model_code ? 'border-red-500' : 'border-border'
                  } ${isEdit ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                />
                {errors.model_code && (
                  <p className="text-xs text-red-500 mt-1">{errors.model_code}</p>
                )}
              </div>

              {/* 模型名称 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  模型名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.model_name}
                  onChange={(e) => handleChange('model_name', e.target.value)}
                  placeholder="如：通义千问Max"
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:border-primary ${
                    errors.model_name ? 'border-red-500' : 'border-border'
                  }`}
                />
                {errors.model_name && (
                  <p className="text-xs text-red-500 mt-1">{errors.model_name}</p>
                )}
              </div>

              {/* 显示名称 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  显示名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) => handleChange('display_name', e.target.value)}
                  placeholder="报价单中显示的名称"
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:border-primary ${
                    errors.display_name ? 'border-red-500' : 'border-border'
                  }`}
                />
                {errors.display_name && (
                  <p className="text-xs text-red-500 mt-1">{errors.display_name}</p>
                )}
              </div>
            </div>
          </div>

          {/* 规格参数 */}
          <div>
            <h3 className="text-sm font-medium text-text-primary mb-4">规格参数</h3>
            <div className="grid grid-cols-2 gap-4">
              {/* 模式 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">模式</label>
                <select
                  value={formData.mode}
                  onChange={(e) => handleChange('mode', e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary bg-white"
                >
                  <option value="">请选择模式</option>
                  {(filterOptions.modes || []).map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  <option value="仅非思考模式">仅非思考模式</option>
                  <option value="非思考和思考模式">非思考和思考模式</option>
                  <option value="仅思考模式">仅思考模式</option>
                </select>
              </div>

              {/* Token阶梯 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">Token阶梯</label>
                <input
                  type="text"
                  value={formData.token_tier}
                  onChange={(e) => handleChange('token_tier', e.target.value)}
                  placeholder="如：0<Token≤32K"
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
                />
              </div>

              {/* 分辨率 */}
              <div>
                <label className="block text-sm text-text-secondary mb-1">分辨率</label>
                <input
                  type="text"
                  value={formData.resolution}
                  onChange={(e) => handleChange('resolution', e.target.value)}
                  placeholder="如：720P、1080P"
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
                />
              </div>

              {/* 复选框 */}
              <div className="flex items-center gap-6 pt-6">
                <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_batch}
                    onChange={(e) => handleChange('supports_batch', e.target.checked)}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>支持Batch半价</span>
                </label>
                <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_cache}
                    onChange={(e) => handleChange('supports_cache', e.target.checked)}
                    className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>支持上下文缓存</span>
                </label>
              </div>
            </div>
          </div>

          {/* 备注 */}
          <div>
            <h3 className="text-sm font-medium text-text-primary mb-4">其他</h3>
            <div>
              <label className="block text-sm text-text-secondary mb-1">备注</label>
              <textarea
                value={formData.remark}
                onChange={(e) => handleChange('remark', e.target.value)}
                placeholder="可选的备注信息"
                rows={3}
                className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary resize-none"
              />
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end gap-3 p-6 border-t border-border">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-6 py-2 text-sm text-text-primary border border-border rounded-lg hover:bg-secondary transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-6 py-2 text-sm text-white bg-primary rounded-lg hover:bg-opacity-90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {isEdit ? '保存' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default PricingModelModal;
