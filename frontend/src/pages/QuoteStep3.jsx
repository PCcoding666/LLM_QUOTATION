/**
 * 步骤3 - 价格清单页面（报价单预览）
 * @description 报价流程第三步：填写客户信息并生成价格清单
 * 按类目分组展示已选模型规格，作为导出报价单的预览
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { exportQuotePreview, downloadExport } from '../api';
import CompetitorModal from '../components/CompetitorModal';
import { useQuote } from '../context/QuoteContext';
import { getDisplayPrice, getUnitLabel } from '../utils/priceConverter';

function QuoteStep3() {
  const navigate = useNavigate();
  
  // 获取价格单位偏好
  const { priceUnit, togglePriceUnit } = useQuote();
  
  // 客户信息
  const [customerName, setCustomerName] = useState('');
  const [quoteDate, setQuoteDate] = useState('');
  const [validUntil, setValidUntil] = useState('');
  
  // 折扣相关状态 (存储折扣百分比，如 10 表示 9折/10% OFF)
  const [discountPercent, setDiscountPercent] = useState(0);
  const [customDiscount, setCustomDiscount] = useState('');
  
  // 模型规格级别的折扣配置: {modelId: {specId: discountPercent}}
  const [specDiscounts, setSpecDiscounts] = useState({});
  
  // 日估计调用量配置: {modelId: {specId: dailyUsage}}
  const [dailyUsages, setDailyUsages] = useState({});
  
  // 常用折扣预设
  const discountPresets = [
    { label: '无折扣', value: 0 },
    { label: '95折', value: 5 },
    { label: '9折', value: 10 },
    { label: '85折', value: 15 },
    { label: '8折', value: 20 },
    { label: '7折', value: 30 },
  ];
  
  // 从前两步获取的数据
  const [selectedModels, setSelectedModels] = useState([]);
  const [modelConfigs, setModelConfigs] = useState({});
  
  // 表单验证错误
  const [errors, setErrors] = useState({});
  
  // 导出加载状态
  const [exporting, setExporting] = useState(false);
  
  // 竞品分析弹窗状态
  const [competitorModalOpen, setCompetitorModalOpen] = useState(false);

  /**
   * 类目配置 - 与 step1 保持一致的 12 个细分分类
   */
  const categoryConfig = {
    text_qwen: { name: '文本生成-通义千问', icon: '💬', priceType: 'token' },
    text_qwen_opensource: { name: '文本生成-通义千问-开源版', icon: '📝', priceType: 'token' },
    text_thirdparty: { name: '文本生成-第三方模型', icon: '🤖', priceType: 'token' },
    image_gen: { name: '图像生成', icon: '🎨', priceType: 'image' },
    image_gen_thirdparty: { name: '图像生成-第三方模型', icon: '🖼️', priceType: 'image' },
    tts: { name: '语音合成', icon: '🔊', priceType: 'character' },
    asr: { name: '语音识别与翻译', icon: '🎤', priceType: 'audio' },
    video_gen: { name: '视频生成', icon: '🎬', priceType: 'video' },
    text_embedding: { name: '文本向量', icon: '📊', priceType: 'token' },
    multimodal_embedding: { name: '多模态向量', icon: '🌐', priceType: 'token' },
    text_nlu: { name: '文本分类抽取排序', icon: '🔍', priceType: 'token' },
    industry: { name: '行业模型', icon: '🏭', priceType: 'token' }
  };

  /**
   * 定义分类渲染顺序
   */
  const categoryOrder = [
    'text_qwen', 'text_qwen_opensource', 'text_thirdparty',
    'image_gen', 'image_gen_thirdparty',
    'tts', 'asr', 'video_gen',
    'text_embedding', 'multimodal_embedding', 'text_nlu', 'industry'
  ];

  /**
   * 计算折扣后价格
   * @param {number} price - 原价
   * @param {number} customDiscountPercent - 自定义折扣百分比（优先使用）
   */
  const calculateDiscountPrice = (price, customDiscountPercent = null) => {
    if (!price || price === null) return null;
    const discountToUse = customDiscountPercent !== null ? customDiscountPercent : discountPercent;
    const discountRate = (100 - discountToUse) / 100;
    return (price * discountRate).toFixed(4);
  };
  
  /**
   * 更新单个规格的折扣
   * @param {number} modelId - 模型ID
   * @param {number} specId - 规格ID
   * @param {number} discount - 折扣百分比
   */
  const updateSpecDiscount = (modelId, specId, discount) => {
    setSpecDiscounts(prev => ({
      ...prev,
      [modelId]: {
        ...(prev[modelId] || {}),
        [specId]: discount
      }
    }));
  };
  
  /**
   * 获取规格的折扣值
   * @param {number} modelId - 模型ID
   * @param {number} specId - 规格ID
   * @returns {number} 折扣百分比
   */
  const getSpecDiscount = (modelId, specId) => {
    return specDiscounts[modelId]?.[specId] ?? discountPercent;
  };
  
  /**
   * 更新单个规格的日估计调用量
   * @param {number} modelId - 模型ID
   * @param {number} specId - 规格ID
   * @param {string} usage - 日估计调用量
   */
  const updateDailyUsage = (modelId, specId, usage) => {
    setDailyUsages(prev => ({
      ...prev,
      [modelId]: {
        ...(prev[modelId] || {}),
        [specId]: usage
      }
    }));
  };
  
  /**
   * 获取规格的日估计调用量
   * @param {number} modelId - 模型ID
   * @param {number} specId - 规格ID
   * @returns {string} 日估计调用量
   */
  const getDailyUsage = (modelId, specId) => {
    return dailyUsages[modelId]?.[specId] || '';
  };

  /**
   * 获取规格的计费单位名称
   * @param {object} spec - 规格对象
   * @param {string} catKey - 类别 key
   * @returns {string} 单位名称
   */
  const getSpecPriceUnit = (spec, catKey) => {
    if (!spec) return '次';
    // 如果有非Token价格，使用其单位
    if (spec.price_unit) return spec.price_unit;
    // 视觉生成类默认用"张"
    if (catKey === 'vision_generate') return '张';
    // Token计费模型根据价格单位偏好
    return getUnitLabel(priceUnit);
  };

  /**
   * 计算预估月费用
   * @param {object} spec - 规格对象
   * @param {string} modelId - 模型ID
   * @param {string} catKey - 类别 key
   * @returns {number|null} 预估月费用
   */
  const calculateMonthlyEstimate = (spec, modelId, catKey) => {
    if (!spec) return null;
    const dailyUsage = parseFloat(getDailyUsage(modelId, spec.id)) || 0;
    if (dailyUsage <= 0) return null;
    
    const discount = getSpecDiscount(modelId, spec.id);
    const discountRate = (100 - discount) / 100;
    
    let unitPrice = 0;
    if (catKey === 'vision_generate') {
      // 视觉生成类：使用单价
      unitPrice = spec.non_token_price || spec.input_price || spec.output_price || 0;
    } else if (spec.non_token_price) {
      // 非Token计费
      unitPrice = spec.non_token_price;
    } else {
      // Token计费：输入+输出的平均价或取输入价
      const inputPrice = spec.input_price || 0;
      const outputPrice = spec.output_price || 0;
      unitPrice = inputPrice + outputPrice; // 简化为输入+输出总和
    }
    
    // 月费用 = 日用量 × 单价 × 30天 × 折扣
    return (dailyUsage * unitPrice * 30 * discountRate).toFixed(2);
  };

  /**
   * 从新版prices数组中提取价格
   */
  const extractPrice = (prices, type) => {
    if (!prices || !Array.isArray(prices)) return null;
    const priceItem = prices.find(p => {
      if (type === 'input') {
        return p.dimension_code === 'input' || p.dimension_code === 'input_token' || p.dimension_code === 'input_token_image';
      } else {
        return p.dimension_code === 'output' || p.dimension_code === 'output_token' || p.dimension_code === 'output_token_thinking';
      }
    });
    return priceItem?.unit_price ?? null;
  };

  /**
   * 提取非Token类型的价格（字符、秒、张等）
   */
  const extractNonTokenPrice = (prices) => {
    if (!prices || !Array.isArray(prices)) return null;
    // 查找非token类型的价格
    const nonTokenTypes = ['character', 'audio_second', 'video_second', 'image_count'];
    const priceItem = prices.find(p => nonTokenTypes.includes(p.dimension_code));
    if (priceItem) {
      return {
        price: priceItem.unit_price,
        dimension_code: priceItem.dimension_code,
        unit: getUnitName(priceItem.dimension_code)
      };
    }
    return null;
  };

  /**
   * 获取计费维度的中文单位名称
   */
  const getUnitName = (dimensionCode) => {
    const unitMap = {
      'character': '字符',
      'audio_second': '秒',
      'video_second': '秒',
      'image_count': '张',
      'input_token': '千Token',
      'output_token': '千Token'
    };
    return unitMap[dimensionCode] || '次';
  };

  /**
   * 根据模型数据获取分类 key
   * 直接使用 model.category 或 sub_category 字段（与 Step1 保持一致）
   */
  const getCategoryKey = (model) => {
    // 优先使用 Step1 保存的 category 或 sub_category 字段
    const category = model.category || model.sub_category || '';
    
    // 如果 category 直接匹配配置的分类 key，则直接返回（不再使用兜底逻辑）
    if (category && categoryConfig[category]) {
      return category;
    }
    
    // 如果没有有效的 category 字段，记录警告并返回默认值
    console.warn('Model missing valid category:', model);
    return 'text_qwen';  // 默认分类
  };

  /**
   * 按类目分组的已配置模型列表（支持多选规格）
   * 每个规格单独一行展示
   * 兼容新版pricing API和旧版products API的数据结构
   */
  const groupedConfigs = useMemo(() => {
    const result = {};
    
    selectedModels.forEach(model => {
      // 兼容新旧版数据结构
      const modelKey = model.model_code || model.id;
      
      // 使用统一的分类函数
      const catKey = getCategoryKey(model);
      
      if (!result[catKey]) {
        result[catKey] = {
          ...categoryConfig[catKey],
          items: []
        };
      }
      
      // 获取配置：支持新版(model_code为key, variants)和旧版(model.id为key, specs)
      const config = modelConfigs[modelKey] || modelConfigs[model.id];
      // 支持多种结构：variants(新), specs(旧多选), spec(旧单选)
      const specs = config?.variants || config?.specs || (config?.spec ? [config.spec] : []);
      
      if (specs.length > 0) {
        // 每个规格单独一行
        specs.forEach((spec, specIndex) => {
          // 提取非Token类型的价格
          const nonTokenPrice = extractNonTokenPrice(spec.prices);
          
          // 转换新版数据结构为Step3期望的格式
          const normalizedSpec = {
            id: spec.id,
            model_name: spec.model_name || model.model_code,
            mode: spec.mode,
            token_range: spec.token_tier || spec.token_range,
            input_price: extractPrice(spec.prices, 'input'),
            output_price: extractPrice(spec.prices, 'output'),
            // 非Token类型价格（字符、秒、张等）
            non_token_price: nonTokenPrice?.price,
            price_unit: nonTokenPrice?.unit,
            dimension_code: nonTokenPrice?.dimension_code,
            remark: spec.remark,
            // 保留原始prices数据便于导出
            prices: spec.prices
          };
          
          result[catKey].items.push({
            model: { ...model, id: modelKey, name: model.model_code || model.name },
            spec: normalizedSpec,
            config,
            isFirstSpec: specIndex === 0,
            totalSpecs: specs.length,
            specIndex
          });
        });
      } else {
        // 没有选择规格时，也显示模型（但价格为空）
        result[catKey].items.push({
          model: { ...model, id: modelKey, name: model.model_code || model.name },
          spec: null,
          config,
          isFirstSpec: true,
          totalSpecs: 0,
          specIndex: 0
        });
      }
    });
    
    return result;
  }, [selectedModels, modelConfigs]);

  useEffect(() => {
    loadPreviousData();
  }, []);

  const loadPreviousData = () => {
    const step1Data = sessionStorage.getItem('quoteStep1');
    const step2Data = sessionStorage.getItem('quoteStep2');
    const step3Data = sessionStorage.getItem('quoteStep3');
    
    if (!step1Data) {
      navigate('/quote/step1');
      return;
    }
    
    const { selectedModels: models } = JSON.parse(step1Data);
    setSelectedModels(models || []);
    
    if (step2Data) {
      const { modelConfigs: configs } = JSON.parse(step2Data);
      setModelConfigs(configs || {});
    }
    
    // 恢复 Step3 保存的客户信息和折扣配置（如果有）
    if (step3Data) {
      const savedData = JSON.parse(step3Data);
      if (savedData.customerName) setCustomerName(savedData.customerName);
      if (savedData.quoteDate) setQuoteDate(savedData.quoteDate);
      if (savedData.validUntil) setValidUntil(savedData.validUntil);
      if (savedData.discountPercent !== undefined) setDiscountPercent(savedData.discountPercent);
      if (savedData.customDiscount) setCustomDiscount(savedData.customDiscount);
      if (savedData.specDiscounts) setSpecDiscounts(savedData.specDiscounts);
    } else {
      // 没有保存的数据时，设置默认日期
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      const todayStr = `${year}-${month}-${day}`;
      setQuoteDate(todayStr);
      
      // 默认有效期为报价日期+1个月
      const validDate = new Date();
      validDate.setMonth(validDate.getMonth() + 1);
      const validYear = validDate.getFullYear();
      const validMonth = String(validDate.getMonth() + 1).padStart(2, '0');
      const validDay = String(validDate.getDate()).padStart(2, '0');
      const validDateStr = `${validYear}-${validMonth}-${validDay}`;
      setValidUntil(validDateStr);
    }
  };

  /**
   * 计算总项数
   */
  const getTotalItems = () => {
    let count = 0;
    Object.values(groupedConfigs).forEach(category => {
      count += category.items.length;
    });
    return count;
  };

  /**
   * 渲染文本/语音类模型表格（按Token计费）
   * 支持同一模型多个规格的展示
   */
  const renderTokenBasedTable = (category, startIndex) => {
    let currentIndex = startIndex;
    
    // 判断是否有任何折扣（整单或单个规格）
    const hasAnyDiscount = discountPercent > 0 || Object.keys(specDiscounts).length > 0;
    
    return (
      <table className="w-full">
        <thead className="bg-secondary">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary w-12">序号</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary">模型名称</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary w-24">模式</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary w-32">Token范围</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">输入单价</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">输出单价</th>
            {hasAnyDiscount && (
              <>
                <th className="px-3 py-3 text-center text-xs font-medium text-text-primary w-32">折扣设置</th>
                <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">折后输入</th>
                <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">折后输出</th>
              </>
            )}
            <th className="px-3 py-3 text-center text-xs font-medium text-text-primary w-36">日估计用量</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">预估月费</th>
          </tr>
        </thead>
        <tbody>
          {category.items.map((item, idx) => {
            const { model, spec, isFirstSpec, totalSpecs, specIndex } = item;
            const rowIndex = currentIndex + idx + 1;
            const hasSpec = spec !== null;
            const monthlyEstimate = calculateMonthlyEstimate(spec, model.id, 'text');
            
            return (
              <tr 
                key={`${model.id}-${specIndex}`} 
                className={`border-t border-border hover:bg-secondary/30 transition-colors ${
                  !isFirstSpec ? 'bg-slate-50/50' : ''
                }`}
              >
                <td className="px-3 py-3 text-sm text-text-secondary text-center">{rowIndex}</td>
                <td className="px-3 py-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary font-medium">
                      {hasSpec ? spec.model_name : model.name}
                    </span>
                    {totalSpecs > 1 && (
                      <span className="px-1.5 py-0.5 bg-purple-50 text-purple-600 text-xs rounded">
                        规格{specIndex + 1}/{totalSpecs}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 text-sm text-text-secondary">
                  {hasSpec && spec.mode ? (
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{spec.mode}</span>
                  ) : '-'}
                </td>
                <td className="px-3 py-3 text-sm text-text-secondary">
                  {hasSpec && spec.token_range && spec.token_range !== '无阶梯计价' 
                    ? <span className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded">{spec.token_range}</span>
                    : '-'
                  }
                </td>
                <td className="px-3 py-3 text-sm text-right">
                  {hasSpec && spec.input_price !== null && spec.input_price !== undefined ? (
                    <>
                      <span className="text-primary font-medium">¥{getDisplayPrice(spec.input_price, priceUnit)}</span>
                      <span className="text-xs text-text-secondary ml-1">/{getUnitLabel(priceUnit)}</span>
                    </>
                  ) : hasSpec && spec.non_token_price !== null && spec.non_token_price !== undefined ? (
                    <>
                      <span className="text-primary font-medium">¥{spec.non_token_price}</span>
                      <span className="text-xs text-text-secondary ml-1">/{spec.price_unit}</span>
                    </>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
                <td className="px-3 py-3 text-sm text-right">
                  {hasSpec && spec.output_price !== null && spec.output_price !== undefined ? (
                    <>
                      <span className="text-green-600 font-medium">¥{getDisplayPrice(spec.output_price, priceUnit)}</span>
                      <span className="text-xs text-text-secondary ml-1">/{getUnitLabel(priceUnit)}</span>
                    </>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
                {hasAnyDiscount && (
                  <>
                    <td className="px-3 py-3 text-sm">
                      {hasSpec && (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            value={getSpecDiscount(model.id, spec.id)}
                            onChange={(e) => updateSpecDiscount(model.id, spec.id, Number(e.target.value))}
                            className="w-16 px-2 py-1 border border-border rounded text-xs text-center focus:border-primary focus:outline-none"
                            placeholder="0"
                          />
                          <span className="text-xs text-text-secondary">%</span>
                          <div className="ml-1 px-1.5 py-0.5 bg-orange-50 text-orange-600 text-xs rounded font-medium whitespace-nowrap">
                            {(10 - getSpecDiscount(model.id, spec.id) / 10).toFixed(1)}折
                          </div>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3 text-sm text-right">
                      {hasSpec && spec.input_price !== null && spec.input_price !== undefined ? (
                        <span className="text-primary font-medium">¥{getDisplayPrice(calculateDiscountPrice(spec.input_price, getSpecDiscount(model.id, spec.id)), priceUnit)}</span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-3 text-sm text-right">
                      {hasSpec && spec.output_price !== null && spec.output_price !== undefined ? (
                        <span className="text-green-600 font-medium">¥{getDisplayPrice(calculateDiscountPrice(spec.output_price, getSpecDiscount(model.id, spec.id)), priceUnit)}</span>
                      ) : '-'}
                    </td>
                  </>
                )}
                <td className="px-3 py-3 text-sm">
                  {hasSpec && (
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={getDailyUsage(model.id, spec.id)}
                        onChange={(e) => updateDailyUsage(model.id, spec.id, e.target.value)}
                        className="w-20 px-2 py-1 border border-border rounded text-xs text-center focus:border-primary focus:outline-none"
                        placeholder="日用量"
                      />
                      <span className="text-xs text-text-secondary whitespace-nowrap">{getSpecPriceUnit(spec, 'text')}</span>
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 text-sm text-right">
                  {monthlyEstimate ? (
                    <span className="text-orange-600 font-medium">¥{monthlyEstimate}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  };

  /**
   * 渲染非Token类模型表格（按次/按张/按字符/按秒计费）
   * 支持同一模型多个规格的展示
   */
  const renderImageBasedTable = (category, startIndex, priceType = 'image') => {
    let currentIndex = startIndex;
    
    // 根据 priceType 获取默认单位
    const getDefaultUnit = (pType) => {
      switch (pType) {
        case 'image': return '张';
        case 'character': return '字符';
        case 'audio': return '秒';
        case 'video': return '秒';
        default: return '次';
      }
    };
    const defaultUnit = getDefaultUnit(priceType);
    
    // 判断是否有任何折扣（整单或单个规格）
    const hasAnyDiscount = discountPercent > 0 || Object.keys(specDiscounts).length > 0;
    
    return (
      <table className="w-full">
        <thead className="bg-secondary">
          <tr>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary w-12">序号</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-text-primary">模型名称</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">单价</th>
            <th className="px-3 py-3 text-center text-xs font-medium text-text-primary w-20">单位</th>
            {hasAnyDiscount && (
              <>
                <th className="px-3 py-3 text-center text-xs font-medium text-text-primary w-32">折扣设置</th>
                <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">折后单价</th>
              </>
            )}
            <th className="px-3 py-3 text-center text-xs font-medium text-text-primary w-36">日估计用量</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-text-primary w-28">预估月费</th>
          </tr>
        </thead>
        <tbody>
          {category.items.map((item, idx) => {
            const { model, spec, isFirstSpec, totalSpecs, specIndex } = item;
            const rowIndex = currentIndex + idx + 1;
            const hasSpec = spec !== null;
            // 使用 non_token_price 或 input_price 作为单价
            const unitPrice = hasSpec ? (spec.non_token_price || spec.input_price || spec.output_price) : null;
            const priceUnitText = hasSpec ? (spec.price_unit || defaultUnit) : defaultUnit;
            const monthlyEstimate = calculateMonthlyEstimate(spec, model.id, priceType);
            
            return (
              <tr 
                key={`${model.id}-${specIndex}`} 
                className={`border-t border-border hover:bg-secondary/30 transition-colors ${
                  !isFirstSpec ? 'bg-slate-50/50' : ''
                }`}
              >
                <td className="px-3 py-3 text-sm text-text-secondary text-center">{rowIndex}</td>
                <td className="px-3 py-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary font-medium">
                      {hasSpec ? spec.model_name : model.name}
                    </span>
                    {totalSpecs > 1 && (
                      <span className="px-1.5 py-0.5 bg-purple-50 text-purple-600 text-xs rounded">
                        规格{specIndex + 1}/{totalSpecs}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 text-sm text-right">
                  {unitPrice !== null && unitPrice !== undefined ? (
                    <span className="text-primary font-medium">¥{unitPrice}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
                <td className="px-3 py-3 text-sm text-center text-text-secondary">
                  /{priceUnitText}
                </td>
                {hasAnyDiscount && (
                  <>
                    <td className="px-3 py-3 text-sm">
                      {hasSpec && (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            value={getSpecDiscount(model.id, spec.id)}
                            onChange={(e) => updateSpecDiscount(model.id, spec.id, Number(e.target.value))}
                            className="w-16 px-2 py-1 border border-border rounded text-xs text-center focus:border-primary focus:outline-none"
                            placeholder="0"
                          />
                          <span className="text-xs text-text-secondary">%</span>
                          <div className="ml-1 px-1.5 py-0.5 bg-orange-50 text-orange-600 text-xs rounded font-medium whitespace-nowrap">
                            {(10 - getSpecDiscount(model.id, spec.id) / 10).toFixed(1)}折
                          </div>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3 text-sm text-right">
                      {unitPrice !== null && unitPrice !== undefined ? (
                        <span className="text-primary font-medium">¥{calculateDiscountPrice(unitPrice, getSpecDiscount(model.id, spec.id))}</span>
                      ) : '-'}
                    </td>
                  </>
                )}
                <td className="px-3 py-3 text-sm">
                  {hasSpec && (
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={getDailyUsage(model.id, spec.id)}
                        onChange={(e) => updateDailyUsage(model.id, spec.id, e.target.value)}
                        className="w-20 px-2 py-1 border border-border rounded text-xs text-center focus:border-primary focus:outline-none"
                        placeholder="日用量"
                      />
                      <span className="text-xs text-text-secondary whitespace-nowrap">{priceUnitText}</span>
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 text-sm text-right">
                  {monthlyEstimate ? (
                    <span className="text-orange-600 font-medium">¥{monthlyEstimate}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  };

  /**
   * 渲染类目模块
   */
  const renderCategorySection = (catKey, startIndex) => {
    const category = groupedConfigs[catKey];
    if (!category || category.items.length === 0) return { element: null, count: 0 };
    
    const priceType = categoryConfig[catKey]?.priceType || 'token';
    const isNonTokenCategory = ['image', 'character', 'audio', 'video'].includes(priceType);
    
    return {
      element: (
        <div key={catKey} className="mb-6">
          {/* 类目标题 */}
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border">
            <span className="text-lg">{category.icon}</span>
            <h3 className="text-base font-medium text-text-primary">{category.name}</h3>
            <span className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded-full">
              {category.items.length} 项
            </span>
          </div>
          
          {/* 表格 */}
          <div className="overflow-x-auto rounded-lg border border-border">
            {isNonTokenCategory 
              ? renderImageBasedTable(category, startIndex, priceType)
              : renderTokenBasedTable(category, startIndex)
            }
          </div>
        </div>
      ),
      count: category.items.length
    };
  };

  // 表单验证
  const validateForm = () => {
    const newErrors = {};
    
    if (!customerName.trim()) {
      newErrors.customerName = '请输入客户名称';
    }
    
    if (!quoteDate) {
      newErrors.quoteDate = '请选择报价日期';
    }
    
    if (!validUntil) {
      newErrors.validUntil = '请选择有效期';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 导出报价
  const handleExport = async () => {
    if (!validateForm()) {
      alert('请先填写完整信息');
      return;
    }
    
    setExporting(true);
    
    try {
      // 构建报价数据
      const quoteData = {
        customerInfo: {
          customerName,
          quoteDate,
          validUntil,
          discountPercent,
          discountRate: (100 - discountPercent) / 100
        },
        selectedModels,
        modelConfigs,
        specDiscounts,
        dailyUsages,  // 添加日估计用量数据
        priceUnit     // 价格单位偏好
      };
      
      // 调用后端 API 生成 Excel
      const response = await exportQuotePreview(quoteData);
      
      if (response.data.success) {
        // 获取下载链接并触发下载
        const downloadUrl = downloadExport(response.data.filename);
        
        // 创建一个临时链接触发下载
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = response.data.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 保存到本地存储（记录历史）
        const existingQuotes = JSON.parse(localStorage.getItem('quotes') || '[]');
        existingQuotes.push({
          id: Date.now(),
          customerInfo: quoteData.customerInfo,
          selectedModels,
          modelConfigs,
          specDiscounts,
          createdAt: new Date().toISOString(),
          exportedFile: response.data.filename
        });
        localStorage.setItem('quotes', JSON.stringify(existingQuotes));
        
        // 清除临时数据
        sessionStorage.removeItem('quoteStep1');
        sessionStorage.removeItem('quoteStep2');
        sessionStorage.removeItem('quoteStep3');
        
        // 提示成功并跳转
        alert('报价单已成功导出！');
        navigate('/');
      } else {
        throw new Error(response.data.detail || '导出失败');
      }
    } catch (error) {
      console.error('导出失败:', error);
      alert(`导出失败: ${error.response?.data?.detail || error.message || '未知错误'}`);
    } finally {
      setExporting(false);
    }
  };



  // 上一步 - 保存当前客户信息和折扣配置后再返回
  const handlePrev = () => {
    // 保存当前客户信息和折扣配置，便于返回时恢复
    sessionStorage.setItem('quoteStep3', JSON.stringify({
      customerName,
      quoteDate,
      validUntil,
      discountPercent,
      customDiscount,
      specDiscounts
    }));
    navigate('/quote/step2');
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* 步骤进度条 */}
      <div className="flex items-center justify-center mb-8">
        <div className="flex items-center">
          <span className="text-text-secondary">模型选择</span>
          <div className="w-24 h-px bg-border mx-4"></div>
          <span className="text-text-secondary">模型配置</span>
          <div className="w-24 h-px bg-border mx-4"></div>
          <span className="text-primary font-medium">价格清单</span>
        </div>
      </div>

      <div className="bg-white border border-border rounded-xl p-6">
        {/* 标题 */}
        <h2 className="text-2xl font-semibold text-text-primary text-center mb-8">
          阿里云大模型产品报价清单
        </h2>

        {/* 客户信息表单 */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              客户名称: <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-primary ${
                errors.customerName ? 'border-red-500' : 'border-border'
              }`}
              placeholder="请输入客户名称"
            />
            {errors.customerName && (
              <p className="text-red-500 text-xs mt-1">{errors.customerName}</p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              报价日期: <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={quoteDate}
              onChange={(e) => setQuoteDate(e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-primary ${
                errors.quoteDate ? 'border-red-500' : 'border-border'
              }`}
            />
            {errors.quoteDate && (
              <p className="text-red-500 text-xs mt-1">{errors.quoteDate}</p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              有效期: <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={validUntil}
              onChange={(e) => setValidUntil(e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:border-primary ${
                errors.validUntil ? 'border-red-500' : 'border-border'
              }`}
            />
            {errors.validUntil && (
              <p className="text-red-500 text-xs mt-1">{errors.validUntil}</p>
            )}
          </div>
        </div>

        {/* 折扣选择器 */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-text-primary mb-3">
            整单统一折扣:
          </label>
          <div className="text-xs text-text-secondary mb-3">
            💡 提示：设置整单折扣后，可在下方表格中为每个模型单独调整折扣
          </div>
          
          {/* 快捷折扣按钮 */}
          <div className="flex flex-wrap gap-2 mb-4">
            {discountPresets.map((preset) => (
              <button
                key={preset.value}
                type="button"
                onClick={() => {
                  setDiscountPercent(preset.value);
                  setCustomDiscount('');
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  discountPercent === preset.value && customDiscount === ''
                    ? 'bg-primary text-white'
                    : 'bg-secondary text-text-primary hover:bg-primary/10 border border-border'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          
          {/* 滑块控制 */}
          <div className="mb-4">
            <div className="flex items-center gap-4">
              <span className="text-sm text-text-secondary w-16">0%</span>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={discountPercent}
                onChange={(e) => {
                  setDiscountPercent(Number(e.target.value));
                  setCustomDiscount('');
                }}
                className="flex-1 h-2 bg-secondary rounded-lg appearance-none cursor-pointer
                           [&::-webkit-slider-thumb]:appearance-none
                           [&::-webkit-slider-thumb]:w-5
                           [&::-webkit-slider-thumb]:h-5
                           [&::-webkit-slider-thumb]:rounded-full
                           [&::-webkit-slider-thumb]:bg-primary
                           [&::-webkit-slider-thumb]:cursor-pointer
                           [&::-webkit-slider-thumb]:shadow-md
                           [&::-webkit-slider-thumb]:transition-all
                           [&::-webkit-slider-thumb]:hover:scale-110"
              />
              <span className="text-sm text-text-secondary w-16 text-right">100%</span>
            </div>
          </div>
          
          {/* 折扣效果预览 */}
          <div className="flex items-center justify-between gap-4 px-4 py-2 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-blue-700">整单折扣:</span>
                <span className="text-lg font-semibold text-primary">
                  {discountPercent > 0 ? `${(10 - discountPercent / 10).toFixed(1)}折` : '无折扣'}
                </span>
              </div>
              <div className="w-px h-6 bg-blue-200"></div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-blue-700">优惠幅度:</span>
                <span className="text-lg font-semibold text-green-600">
                  {discountPercent > 0 ? `-${discountPercent}%` : '0%'}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                // 批量应用整单折扣到所有规格
                const newSpecDiscounts = {};
                selectedModels.forEach(model => {
                  const config = modelConfigs[model.id];
                  const specs = config?.specs || [];
                  if (specs.length > 0) {
                    newSpecDiscounts[model.id] = {};
                    specs.forEach(spec => {
                      newSpecDiscounts[model.id][spec.id] = discountPercent;
                    });
                  }
                });
                setSpecDiscounts(newSpecDiscounts);
              }}
              className="px-4 py-1.5 bg-primary text-white text-xs rounded-lg hover:bg-opacity-90 transition-all"
            >
              应用到所有模型
            </button>
          </div>
        </div>

        {/* 价目表预览 */}
        <div className="mb-8">
          {/* 报价单标题区域 */}
          <div className="bg-gradient-to-r from-blue-50 to-white rounded-lg p-4 mb-4 border border-blue-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-medium text-text-primary">报价明细预览</h3>
                  <p className="text-xs text-text-secondary">共 {getTotalItems()} 项产品</p>
                </div>
              </div>
              {discountPercent > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-orange-50 rounded-lg">
                  <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5 2a2 2 0 00-2 2v14l3.5-2 3.5 2 3.5-2 3.5 2V4a2 2 0 00-2-2H5zm2.5 3a1.5 1.5 0 100 3 1.5 1.5 0 000-3zm6.207.293a1 1 0 00-1.414 0l-6 6a1 1 0 101.414 1.414l6-6a1 1 0 000-1.414zM12.5 10a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium text-orange-600">
                    整单 {(10 - discountPercent / 10).toFixed(1)}折
                  </span>
                </div>
              )}
            </div>
          </div>
          
          {/* 单位切换开关 */}
          <div className="flex items-center justify-end mb-3">
            <div className="flex items-center gap-3 px-3 py-2 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-sm text-text-secondary whitespace-nowrap">价格单位:</span>
              <div className="inline-flex rounded-lg bg-gray-200 p-0.5">
                <button
                  onClick={() => priceUnit !== 'thousand' && togglePriceUnit()}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
                    priceUnit === 'thousand'
                      ? 'bg-white text-primary shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  千Token
                </button>
                <button
                  onClick={() => priceUnit !== 'million' && togglePriceUnit()}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap ${
                    priceUnit === 'million'
                      ? 'bg-white text-primary shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  百万Token
                </button>
              </div>
              <span className="text-xs text-blue-600 whitespace-nowrap">
                {priceUnit === 'million' ? '(行业通用)' : '(原始单位)'}
              </span>
            </div>
          </div>
          
          {/* 价目表内容 */}
          <div className="border border-border rounded-xl p-6 bg-white min-h-[300px]">
            {selectedModels.length > 0 ? (
              <div>
                {(() => {
                  let currentIndex = 0;
                  const sections = [];
                  
                  // 按固定顺序渲染各类目（使用新的 12 分类）
                  categoryOrder.forEach(catKey => {
                    const result = renderCategorySection(catKey, currentIndex);
                    if (result.element) {
                      sections.push(result.element);
                      currentIndex += result.count;
                    }
                  });
                  
                  return sections;
                })()}
                
                {/* 报价说明 */}
                <div className="mt-6 p-4 bg-secondary rounded-lg">
                  <h4 className="text-sm font-medium text-text-primary mb-2">报价说明</h4>
                  <ul className="text-xs text-text-secondary space-y-1.5">
                    <li>• 以上价格均为人民币（CNY）计价</li>
                    <li>• Token计费模型按实际调用量结算</li>
                    <li>• 视觉生成模型按图片生成数量结算</li>
                  </ul>
                  
                  {/* 折扣信息展示 */}
                  {(discountPercent > 0 || Object.keys(specDiscounts).length > 0) && (() => {
                    // 收集所有规格及其折扣
                    const allSpecs = [];
                    selectedModels.forEach(model => {
                      const config = modelConfigs[model.id];
                      const specs = config?.specs || (config?.spec ? [config.spec] : []);
                      specs.forEach(spec => {
                        const specDiscount = getSpecDiscount(model.id, spec.id);
                        allSpecs.push({
                          modelName: spec.model_name || model.name,
                          specName: spec.mode || spec.token_range || '',
                          discount: specDiscount,
                          discountLabel: (10 - specDiscount / 10).toFixed(1) + '折'
                        });
                      });
                    });
                    
                    // 找出与整单折扣不同的规格
                    const specialSpecs = allSpecs.filter(s => s.discount !== discountPercent);
                    const hasSpecialDiscounts = specialSpecs.length > 0;
                    
                    return (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        {/* 整单折扣标签 */}
                        <div className="flex items-center gap-2 mb-3">
                          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 rounded-lg border border-orange-100">
                            <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5 2a2 2 0 00-2 2v14l3.5-2 3.5 2 3.5-2 3.5 2V4a2 2 0 00-2-2H5zm2.5 3a1.5 1.5 0 100 3 1.5 1.5 0 000-3zm6.207.293a1 1 0 00-1.414 0l-6 6a1 1 0 101.414 1.414l6-6a1 1 0 000-1.414zM12.5 10a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" clipRule="evenodd" />
                            </svg>
                            <span className="text-xs text-orange-700">本报价单默认折扣</span>
                            <span className="text-sm font-semibold text-orange-600">
                              {discountPercent > 0 ? `${(10 - discountPercent / 10).toFixed(1)}折` : '无折扣'}
                            </span>
                          </div>
                          {hasSpecialDiscounts && (
                            <span className="text-xs text-text-secondary">
                              (部分模型享有不同折扣)
                            </span>
                          )}
                        </div>
                        
                        {/* 特殊折扣模型列表 */}
                        {hasSpecialDiscounts && (
                          <div className="bg-white rounded-lg border border-border p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <span className="text-xs font-medium text-text-primary">特殊折扣模型</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {specialSpecs.map((spec, idx) => (
                                <div 
                                  key={idx}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-full border border-blue-100"
                                >
                                  <span className="text-xs text-text-primary max-w-32 truncate" title={spec.modelName}>
                                    {spec.modelName}
                                  </span>
                                  {spec.specName && (
                                    <span className="text-xs text-text-secondary">·</span>
                                  )}
                                  {spec.specName && (
                                    <span className="text-xs text-text-secondary max-w-20 truncate" title={spec.specName}>
                                      {spec.specName}
                                    </span>
                                  )}
                                  <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                                    spec.discount > discountPercent 
                                      ? 'bg-green-100 text-green-600' 
                                      : 'bg-orange-100 text-orange-600'
                                  }`}>
                                    {spec.discountLabel}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">📋</div>
                <p className="text-text-secondary">暂无已选模型</p>
              </div>
            )}
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end gap-4 pt-6 border-t border-border">
          <button
            onClick={handlePrev}
            className="px-8 py-3 bg-white text-text-primary border border-border rounded-lg font-medium hover:bg-secondary transition-all"
          >
            上一步
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className={`px-8 py-3 bg-primary text-white rounded-lg font-medium transition-all flex items-center gap-2 ${exporting ? 'opacity-70 cursor-not-allowed' : 'hover:bg-opacity-90'}`}
          >
            {exporting ? (
              <>
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                导出中...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                导出报价单
              </>
            )}
          </button>
          <button
            onClick={() => setCompetitorModalOpen(true)}
            className="px-8 py-3 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-all flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            竞争分析
          </button>
        </div>
      </div>
      
      {/* 竞品分析弹窗 */}
      <CompetitorModal 
        isOpen={competitorModalOpen}
        onClose={() => setCompetitorModalOpen(false)}
        models={selectedModels}
      />
    </div>
  );
}

export default QuoteStep3;
