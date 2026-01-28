import client from './client';

export const getCategories = () => client.get('/products/categories/list');

export const getModels = (params = {}) => 
  client.get('/products/models', { params });

export const getModelPricing = (productCode, region = 'cn-beijing') => 
  client.get(`/products/${productCode}/price`, { params: { region } });

// 根据模型显示名称获取数据库规格配置
export const getModelSpecs = (displayName) =>
  client.get('/products/specs', { params: { model_name: displayName } });

// 获取筛选条件选项
export const getFilterOptions = () => client.get('/products/filters');

export const calculateQuote = (data) => 
  client.post('/quotes/calculate', data);

export const getQuotes = (page = 1, pageSize = 20, keyword = '', categoryCode = '') =>
  client.get('/quotes', { 
    params: { 
      page, 
      page_size: pageSize,
      keyword: keyword || undefined,
      category_code: categoryCode || undefined
    } 
  });

// 获取报价统计数据
export const getQuoteStatistics = () => client.get('/quotes/statistics');

// 获取报价详情
export const getQuoteDetail = (quoteId) => client.get(`/quotes/${quoteId}`);

export const exportQuote = (quoteId, templateType = 'standard') =>
  client.post('/export/excel', { quote_id: quoteId, template_type: templateType });

export const downloadExport = (filename) =>
  `/api/v1/export/download/file/${encodeURIComponent(filename)}`;

/**
 * 导出报价预览为Excel文件
 * @param {Object} quoteData - 报价数据，包含客户信息、已选模型、配置和折扣
 * @returns {Promise} 返回包含下载链接的响应
 */
export const exportQuotePreview = (quoteData) =>
  client.post('/export/preview', quoteData);

// ===== AI 智能助手 API =====

/**
 * 发送聊天消息给 AI 助手
 * @param {string} message - 用户消息
 * @param {string} sessionId - 会话ID（可选）
 * @returns {Promise} AI 响应
 */
export const sendChatMessage = (message, sessionId = null) =>
  client.post('/ai/chat', { 
    message, 
    session_id: sessionId 
  });

/**
 * 上传文件并提取信息（支持Excel、PDF、图片等）
 * @param {File} file - 要上传的文件
 * @returns {Promise} 提取结果
 */
export const extractFromFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return client.post('/ai/extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * 清除会话历史
 * @param {string} sessionId - 会话ID
 */
export const clearChatSession = (sessionId) =>
  client.delete(`/ai/session/${sessionId}`);

// =====================================================
// 定价数据 API（基于pricing_*表，提供多维度定价查询）
// =====================================================

/**
 * 获取定价筛选选项（多维度）
 * @returns {Promise} 筛选选项列表
 */
export const getPricingFilters = () => 
  client.get('/products/pricing/filters');

/**
 * 获取定价模型列表（多维度筛选）
 * @param {Object} params - 筛选参数
 * @param {string} [params.category] - 分类代码
 * @param {string} [params.mode] - 模式（仅非思考模式/非思考和思考模式/仅思考模式）
 * @param {string} [params.token_tier] - Token阶梯
 * @param {string} [params.resolution] - 分辨率（视频模型）
 * @param {boolean} [params.supports_batch] - 是否支持Batch半价
 * @param {boolean} [params.supports_cache] - 是否支持上下文缓存
 * @param {string} [params.keyword] - 关键词搜索
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @returns {Promise} 模型列表
 */
export const getPricingModels = (params = {}) =>
  client.get('/products/pricing/models', { params });

/**
 * 获取模型完整定价信息（所有变体）
 * @param {string} modelCode - 模型代码
 * @returns {Promise} 模型定价详情
 */
export const getModelPricingDetail = (modelCode) =>
  client.get(`/products/pricing/model/${encodeURIComponent(modelCode)}`);

/**
 * 获取模型定价摘要
 * @param {string} modelCode - 模型代码
 * @returns {Promise} 定价摘要
 */
export const getModelPricingSummary = (modelCode) =>
  client.get(`/products/pricing/summary/${encodeURIComponent(modelCode)}`);

/**
 * 搜索模型（用于自动完成）
 * @param {string} keyword - 搜索关键词
 * @param {number} [limit] - 返回数量限制
 * @returns {Promise} 搜索结果
 */
export const searchPricingModels = (keyword, limit = 20) =>
  client.get('/products/pricing/search', { params: { keyword, limit } });

/**
 * 获取分类及模型树
 * @returns {Promise} 分类模型树结构
 */
export const getPricingCategories = () =>
  client.get('/products/pricing/categories');

// =====================================================
// 竞品分析 API
// =====================================================

/**
 * 获取单个模型的竞品对标数据
 * @param {string} modelName - 模型代码
 * @param {string} [category] - 可选类别过滤
 * @returns {Promise} 竞品对标数据
 */
export const getCompetitorMatch = (modelName, category = null) =>
  client.get('/competitors/match', { 
    params: { 
      model_name: modelName,
      category: category || undefined
    } 
  });

/**
 * 批量获取多个模型的竞品对标数据
 * @param {string[]} modelCodes - 模型代码列表
 * @returns {Promise} 批量竞品对标数据
 */
export const batchGetCompetitors = (modelCodes) =>
  client.post('/competitors/batch-match', { model_codes: modelCodes });

/**
 * 获取竞品数据服务状态
 * @returns {Promise} 服务状态信息
 */
export const getCompetitorStatus = () =>
  client.get('/competitors/status');

// =====================================================
// 定价管理 API（用于模型规格与价格的 CRUD 操作）
// =====================================================

/**
 * 获取管理端模型列表
 * @param {Object} params - 筛选参数
 * @returns {Promise} 分页模型列表
 */
export const getPricingModelsAdmin = (params = {}) =>
  client.get('/pricing-admin/models', { params });

/**
 * 获取管理端模型详情
 * @param {number} modelId - 模型ID
 * @returns {Promise} 模型详情
 */
export const getPricingModelAdminDetail = (modelId) =>
  client.get(`/pricing-admin/models/${modelId}`);

/**
 * 创建模型
 * @param {Object} data - 模型数据
 * @returns {Promise} 创建结果
 */
export const createPricingModel = (data) =>
  client.post('/pricing-admin/models', data);

/**
 * 更新模型
 * @param {number} modelId - 模型ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export const updatePricingModel = (modelId, data) =>
  client.put(`/pricing-admin/models/${modelId}`, data);

/**
 * 删除模型（软删除）
 * @param {number} modelId - 模型ID
 * @returns {Promise} 删除结果
 */
export const deletePricingModel = (modelId) =>
  client.delete(`/pricing-admin/models/${modelId}`);

/**
 * 批量删除模型（软删除）
 * @param {number[]} modelIds - 模型ID列表
 * @returns {Promise} 删除结果
 */
export const batchDeletePricingModels = (modelIds) =>
  client.post('/pricing-admin/models/batch-delete', { model_ids: modelIds });

/**
 * 获取模型价格列表
 * @param {number} modelId - 模型ID
 * @returns {Promise} 价格列表
 */
export const getModelPricesAdmin = (modelId) =>
  client.get(`/pricing-admin/models/${modelId}/prices`);

/**
 * 添加模型价格维度
 * @param {number} modelId - 模型ID
 * @param {Object} data - 价格数据
 * @returns {Promise} 添加结果
 */
export const addModelPrice = (modelId, data) =>
  client.post(`/pricing-admin/models/${modelId}/prices`, data);

/**
 * 更新价格
 * @param {number} priceId - 价格ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export const updateModelPrice = (priceId, data) =>
  client.put(`/pricing-admin/prices/${priceId}`, data);

/**
 * 删除价格
 * @param {number} priceId - 价格ID
 * @returns {Promise} 删除结果
 */
export const deleteModelPrice = (priceId) =>
  client.delete(`/pricing-admin/prices/${priceId}`);

/**
 * 获取管理端分类列表
 * @returns {Promise} 分类列表
 */
export const getPricingCategoriesAdmin = () =>
  client.get('/pricing-admin/categories');

/**
 * 获取管理端筛选选项
 * @returns {Promise} 筛选选项
 */
export const getPricingFiltersAdmin = () =>
  client.get('/pricing-admin/filters');
