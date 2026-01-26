/**
 * 价格单位转换工具
 * @description 支持 千Token ↔ 百万Token 的价格转换
 */

// 需要转换的Token单位列表
const TOKEN_UNITS = ['千Token', '千tokens', '千token'];

/**
 * 判断是否为Token计费单位
 * @param {string} unit - 单位字符串
 * @returns {boolean}
 */
export const isTokenUnit = (unit) => {
  if (!unit) return false;
  return TOKEN_UNITS.some(t => unit.includes(t) || unit.toLowerCase().includes('token'));
};

/**
 * 转换价格：千Token → 百万Token
 * @param {number} price - 原价（千Token）
 * @returns {number|null}
 */
export const toMillionToken = (price) => {
  if (price === null || price === undefined) return null;
  return Number((price * 1000).toFixed(4));
};

/**
 * 转换价格：百万Token → 千Token
 * @param {number} price - 原价（百万Token）
 * @returns {number|null}
 */
export const toThousandToken = (price) => {
  if (price === null || price === undefined) return null;
  return Number((price / 1000).toFixed(6));
};

/**
 * 根据单位偏好获取显示价格
 * @param {number} price - 原始价格（千Token）
 * @param {string} priceUnit - 单位偏好 'million' | 'thousand'
 * @returns {number|null}
 */
export const getDisplayPrice = (price, priceUnit = 'thousand') => {
  if (price === null || price === undefined) return null;
  return priceUnit === 'million' ? toMillionToken(price) : price;
};

/**
 * 获取显示单位文本
 * @param {string} priceUnit - 单位偏好 'million' | 'thousand'
 * @returns {string}
 */
export const getUnitLabel = (priceUnit = 'thousand') => {
  return priceUnit === 'million' ? '百万Token' : '千Token';
};
