/**
 * 极速报价页面 - 通过AI对话完成报价单生成
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { sendExpressQuoteMessage, exportExpressQuote, getExpressQuoteWelcome, downloadExport } from '../api';
import styles from './ExpressQuote.module.css';

// 进度步骤配置
const STEPS = [
  { key: 1, label: '选择模型', icon: '📋' },
  { key: 2, label: '配置规格', icon: '⚙️' },
  { key: 3, label: '客户信息', icon: '👤' },
  { key: 4, label: '预览导出', icon: '📥' }
];

export default function ExpressQuote() {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  // 状态
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [collectedData, setCollectedData] = useState({
    selectedModels: [],
    modelConfigs: {},
    customerInfo: {}
  });
  const [suggestedOptions, setSuggestedOptions] = useState([]);
  const [readyToExport, setReadyToExport] = useState(false);
  const [previewTable, setPreviewTable] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  
  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);
  
  // 初始化欢迎消息
  useEffect(() => {
    const initWelcome = async () => {
      try {
        const response = await getExpressQuoteWelcome();
        const data = response.data;
        setMessages([{
          role: 'assistant',
          content: data.message
        }]);
        setSuggestedOptions(data.suggested_options || []);
      } catch (error) {
        setMessages([{
          role: 'assistant',
          content: '我是报价侠，我可以帮您快速生成大模型报价单。请告诉我您需要哪些模型？\n\n您可以：\n• 直接说模型名称（如 qwen3-max）\n• 选择具体规格信息，输出报单预览\n• 预览后可以继续追加模型规格'
        }]);
        setSuggestedOptions(['qwen3-Max', 'qwen-Plus', 'qwen-Flash', 'qwen3-vl-plus', 'qwen3-vl-flash', 'qwen3-asr-flash', 'qwen3-tts-flash', 'Qwen-image', 'wan2.6-t2v']);
      }
    };
    initWelcome();
  }, []);
  
  // 发送消息
  const handleSend = async (message) => {
    if (!message.trim() || isLoading) return;
    
    const userMessage = message.trim();
    setInputValue('');
    setIsLoading(true);
    
    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    
    try {
      const response = await sendExpressQuoteMessage(userMessage, sessionId);
      const data = response.data;
      
      // 更新会话ID
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      
      // 添加AI响应
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      
      // 更新状态
      setCurrentStep(data.current_step || 1);
      setCollectedData(data.collected_data || {});
      setSuggestedOptions(data.suggested_options || []);
      setReadyToExport(data.ready_to_export || false);
      
      // 处理预览表格
      if (data.preview_table) {
        try {
          setPreviewTable(JSON.parse(data.preview_table));
        } catch (e) {
          setPreviewTable(null);
        }
      }
      
    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '抱歉，处理请求时出现错误，请重试。'
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };
  
  // 处理快捷选项点击
  const handleOptionClick = (option) => {
    handleSend(option);
  };
  
  // 导出报价单
  const handleExport = async () => {
    if (!sessionId || isExporting) return;
    
    setIsExporting(true);
    try {
      const response = await exportExpressQuote(sessionId);
      const data = response.data;
      
      if (data.success && data.filename) {
        // 触发下载
        const downloadUrl = downloadExport(data.filename);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = data.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `🎉 报价单已生成！文件名：${data.filename}\n\n点击下载按钮保存文件。`
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ 导出失败：${data.message}`
        }]);
      }
    } catch (error) {
      console.error('导出失败:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '导出失败，请重试。'
      }]);
    } finally {
      setIsExporting(false);
    }
  };
  
  // 重新开始
  const handleRestart = () => {
    setSessionId(null);
    setMessages([{
      role: 'assistant',
      content: '我是报价侠，我可以帮您快速生成大模型报价单。请告诉我您需要哪些模型？\n\n您可以：\n• 直接说模型名称（如 qwen3-max）\n• 选择具体规格信息，输出报单预览\n• 预览后可以继续追加模型规格'
    }]);
    setCurrentStep(1);
    setCollectedData({ selectedModels: [], modelConfigs: {}, customerInfo: {} });
    setSuggestedOptions(['qwen3-Max', 'qwen-Plus', 'qwen-Flash', 'qwen3-vl-plus', 'qwen3-vl-flash', 'qwen3-asr-flash', 'qwen3-tts-flash', 'Qwen-image', 'wan2.6-t2v']);
    setReadyToExport(false);
    setPreviewTable(null);
  };
  
  // 渲染消息内容
  const renderMessageContent = (content) => {
    // 简单的Markdown渲染
    return content.split('\n').map((line, idx) => (
      <React.Fragment key={idx}>
        {line}
        {idx < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };
  
  // 模型分类配置
  const categoryConfig = {
    text_qwen: { name: '文本生成-通义千问', icon: '💬', priceType: 'token' },
    text_thirdparty: { name: '文本生成-第三方模型', icon: '🤖', priceType: 'token' },
    image_gen: { name: '图像生成', icon: '🎨', priceType: 'image' },
    tts: { name: '语音合成', icon: '🔊', priceType: 'character' },
    asr: { name: '语音识别', icon: '🎤', priceType: 'audio' },
    video_gen: { name: '视频生成', icon: '🎬', priceType: 'video' },
    text_embedding: { name: '文本向量', icon: '📊', priceType: 'token' }
  };

  // 根据模型名称判断分类
  const getCategoryKey = (modelName) => {
    const name = (modelName || '').toLowerCase();
    
    // 图像生成类
    if (name.includes('wanx') || name.includes('flux') || name.includes('stable-diffusion') ||
        name.includes('qwen-image') || name.includes('image')) {
      return 'image_gen';
    }
    // 视频生成类
    if (name.includes('t2v') || name.includes('i2v') || name.startsWith('wan2')) {
      return 'video_gen';
    }
    // 语音合成类
    if (name.includes('-tts') || name.includes('cosyvoice')) {
      return 'tts';
    }
    // 语音识别类
    if (name.includes('-asr') || name.includes('paraformer') || name.includes('sensevoice')) {
      return 'asr';
    }
    // 向量模型
    if (name.includes('embedding')) {
      return 'text_embedding';
    }
    // 第三方文本模型
    if (name.includes('deepseek') || name.includes('llama') || name.includes('baichuan')) {
      return 'text_thirdparty';
    }
    // 默认归入通义千问文本类
    return 'text_qwen';
  };

  // 按分类对rows进行分组
  const groupRowsByCategory = (rows) => {
    const grouped = {};
    rows.forEach(row => {
      const catKey = getCategoryKey(row.model);
      if (!grouped[catKey]) {
        grouped[catKey] = {
          ...categoryConfig[catKey],
          items: []
        };
      }
      grouped[catKey].items.push(row);
    });
    return grouped;
  };

  // 渲染Token类表格（有输入/输出价格）
  const renderTokenTable = (items, hasDiscount) => (
    <table className={styles.previewTable}>
      <thead>
        <tr>
          <th>序号</th>
          <th>模型</th>
          <th>模式</th>
          <th>Token范围</th>
          <th>输入单价</th>
          <th>输出单价</th>
          {hasDiscount && <th>折后入价</th>}
          {hasDiscount && <th>折后出价</th>}
        </tr>
      </thead>
      <tbody>
        {items.map((row, idx) => (
          <tr key={idx}>
            <td>{row.idx}</td>
            <td>{row.model}</td>
            <td>{row.mode}</td>
            <td>{row.token_tier}</td>
            <td>{row.input_price}</td>
            <td>{row.output_price}</td>
            {hasDiscount && <td>{row.input_discounted}</td>}
            {hasDiscount && <td>{row.output_discounted}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );

  // 渲染非Token类表格（图像/视频/语音，单价格）
  const renderNonTokenTable = (items, hasDiscount, priceType) => {
    const unitMap = { image: '张', video: '秒', character: '字符', audio: '秒' };
    const defaultUnit = unitMap[priceType] || '次';
    
    return (
      <table className={styles.previewTable}>
        <thead>
          <tr>
            <th>序号</th>
            <th>模型</th>
            <th>模式</th>
            <th>单价</th>
            <th>单位</th>
            {hasDiscount && <th>折后单价</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((row, idx) => {
            // 使用后端返回的price_unit，或根据分类使用默认单位
            const unit = row.price_unit || defaultUnit;
            return (
              <tr key={idx}>
                <td>{row.idx}</td>
                <td>{row.model}</td>
                <td>{row.mode || '-'}</td>
                <td>{row.input_price}</td>
                <td>/{unit}</td>
                {hasDiscount && <td>{row.input_discounted}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  };

  // 渲染预览表格（按分类分表格展示）
  const renderPreviewTable = () => {
    if (!previewTable || !previewTable.rows || previewTable.rows.length === 0) {
      return null;
    }
    
    const { customerInfo, rows } = previewTable;
    const groupedData = groupRowsByCategory(rows);
    const hasDiscount = customerInfo && customerInfo.discountPercent > 0;
    
    // 分类渲染顺序
    const categoryOrder = ['text_qwen', 'text_thirdparty', 'text_embedding', 'image_gen', 'video_gen', 'tts', 'asr'];
    
    return (
      <div className={styles.previewContainer}>
        <div className={styles.previewHeader}>
          <h3>📋 报价单预览</h3>
          {customerInfo && (
            <div className={styles.customerInfo}>
              <span>客户：{customerInfo.customerName}</span>
              <span>日期：{customerInfo.quoteDate}</span>
              <span>有效期：{customerInfo.validUntil}</span>
              {customerInfo.discountPercent > 0 && (
                <span>折扣：{(10 - customerInfo.discountPercent / 10).toFixed(1)}折</span>
              )}
            </div>
          )}
        </div>
        
        {/* 按分类渲染表格 */}
        {categoryOrder.map(catKey => {
          const category = groupedData[catKey];
          if (!category || category.items.length === 0) return null;
          
          const isTokenBased = category.priceType === 'token';
          
          return (
            <div key={catKey} className={styles.categorySection}>
              <div className={styles.categoryHeader}>
                <span className={styles.categoryIcon}>{category.icon}</span>
                <span className={styles.categoryName}>{category.name}</span>
                <span className={styles.categoryCount}>{category.items.length} 项</span>
              </div>
              <div className={styles.tableWrapper}>
                {isTokenBased 
                  ? renderTokenTable(category.items, hasDiscount)
                  : renderNonTokenTable(category.items, hasDiscount, category.priceType)
                }
              </div>
            </div>
          );
        })}
      </div>
    );
  };
  
  return (
    <div className={styles.container}>
      {/* 顶部导航 */}
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate('/')}>
          ← 返回首页
        </button>
        <h1 className={styles.title}>⚡ 极速报价</h1>
        <button className={styles.restartButton} onClick={handleRestart}>
          🔄 重新开始
        </button>
      </header>
      
      {/* 进度条 */}
      <div className={styles.progressBar}>
        {STEPS.map((step, idx) => (
          <div
            key={step.key}
            className={`${styles.step} ${currentStep >= step.key ? styles.stepActive : ''}`}
          >
            <span className={styles.stepIcon}>{step.icon}</span>
            <span className={styles.stepLabel}>{step.label}</span>
            {idx < STEPS.length - 1 && <div className={styles.stepLine} />}
          </div>
        ))}
      </div>
      
      {/* 主内容区 */}
      <div className={styles.mainContent}>
        {/* 对话区 */}
        <div className={styles.chatArea}>
          <div className={styles.messageList}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`${styles.message} ${msg.role === 'user' ? styles.userMessage : styles.assistantMessage}`}
              >
                {msg.role === 'assistant' && (
                  <div className={styles.avatar}>🤖</div>
                )}
                <div className={styles.messageContent}>
                  {renderMessageContent(msg.content)}
                </div>
                {msg.role === 'user' && (
                  <div className={styles.avatar}>👤</div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className={`${styles.message} ${styles.assistantMessage}`}>
                <div className={styles.avatar}>🤖</div>
                <div className={styles.messageContent}>
                  <div className={styles.typingIndicator}>
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          {/* 预览表格 */}
          {previewTable && renderPreviewTable()}
          
          {/* 快捷选项 */}
          {suggestedOptions.length > 0 && (
            <div className={styles.suggestedOptions}>
              {suggestedOptions.map((option, idx) => (
                <button
                  key={idx}
                  className={styles.optionButton}
                  onClick={() => handleOptionClick(option)}
                  disabled={isLoading}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
          
          {/* 导出按钮 */}
          {readyToExport && (
            <div className={styles.exportArea}>
              <button
                className={styles.exportButton}
                onClick={handleExport}
                disabled={isExporting}
              >
                {isExporting ? '⏳ 正在生成...' : '📥 导出Excel报价单'}
              </button>
            </div>
          )}
          
          {/* 输入区 */}
          <div className={styles.inputArea}>
            <input
              ref={inputRef}
              type="text"
              className={styles.input}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend(inputValue)}
              placeholder="输入消息，或点击上方快捷选项..."
              disabled={isLoading}
            />
            <button
              className={styles.sendButton}
              onClick={() => handleSend(inputValue)}
              disabled={isLoading || !inputValue.trim()}
            >
              发送
            </button>
          </div>
        </div>
        
        {/* 侧边栏数据摘要 */}
        <aside className={styles.sidebar}>
          <h3 className={styles.sidebarTitle}>📊 报价单摘要</h3>
          
          {/* 已选模型 */}
          <div className={styles.summarySection}>
            <h4>已选模型 ({collectedData.selectedModels?.length || 0})</h4>
            {collectedData.selectedModels?.length > 0 ? (
              <ul className={styles.modelList}>
                {collectedData.selectedModels.map((model, idx) => (
                  <li key={idx}>
                    {model.display_name || model.model_code || model.model_name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.emptyHint}>暂无选择</p>
            )}
          </div>
          
          {/* 客户信息 */}
          <div className={styles.summarySection}>
            <h4>客户信息</h4>
            {collectedData.customerInfo?.customerName ? (
              <div className={styles.customerDetail}>
                <p><strong>客户：</strong>{collectedData.customerInfo.customerName}</p>
                {collectedData.customerInfo.discountPercent > 0 && (
                  <p><strong>折扣：</strong>{(10 - collectedData.customerInfo.discountPercent / 10).toFixed(1)}折</p>
                )}
              </div>
            ) : (
              <p className={styles.emptyHint}>待填写</p>
            )}
          </div>
          
          {/* 当前步骤 */}
          <div className={styles.summarySection}>
            <h4>当前步骤</h4>
            <p className={styles.currentStepText}>
              {STEPS.find(s => s.key === currentStep)?.icon} {STEPS.find(s => s.key === currentStep)?.label}
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
