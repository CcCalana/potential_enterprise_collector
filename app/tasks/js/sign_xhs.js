// 新建 sign_xhs.js —— 基于开源库 xiaohongshu-sign-js 生成 x-s / x-t
// 使用前请在项目根执行：  npm install xiaohongshu-sign-js

// 替换为基于浏览器原厂脚本 seccore_signv2 的实现，避免依赖失效的第三方包
// const { seccore_signv2 } = require('./origin_xhs_sign');

// ========== 浏览器环境打桩 ==========
if (typeof global.window === 'undefined') global.window = global;
if (typeof global.self === 'undefined') global.self = global;
if (typeof global.document === 'undefined') global.document = {};

// ========== 动态加载签名脚本 ==========
// 将你抓取到的含 seccore_signv2 的 nuxt js 文件放在同目录，并在此 require。
// 可按需新增更多文件名。
const vendorFiles = [
  './webmsxyw.js',                  // 示例：真正包含签名函数的脚本
  './webmsxyw.8fd3c6e.js',          // 示例：带 hash
  './vendor-dynamic.4f7b1174.js',   // 你已保存的文件
  './origin_xhs_sign.js',           // 旧版占位
];

for (const f of vendorFiles) {
  try {
    require(f);
  } catch (_) {
    /* ignore if file not exist */
  }
}

// ========== 获取签名核心函数 ==========
const signCore =
  global.seccore_signv2 ||
  global._seccore_signv2 ||
  global._webmsxyw       ||
  (typeof global.module !== 'undefined' && global.module.exports && (
    global.module.exports.seccore_signv2 || global.module.exports._webmsxyw
  )) ||
  null;

if (!signCore) {
  throw new Error('未能在已加载的脚本中找到 seccore_signv2，请确认已保存并正确 require 含签名函数的 nuxt 文件');
}

// ========== 对外统一接口 ==========
/**
 * 生成小红书接口所需的 X-s / X-t 签名。
 * 兼容 Python 端调用签名：get_sign(url, dataJson, cookie)
 * @param {string} url        请求完整 URL
 * @param {string} dataJson   JSON.stringify(payload)；GET 请求可传空字符串
 * @param {string} cookie     预留字段，目前签名算法不依赖 Cookie
 * @returns {{'x-s': string, 'x-t': string}}
 */
function get_sign(url, dataJson = '', cookie = '') {
  let data = '';
  if (dataJson && typeof dataJson === 'string' && dataJson.trim() !== '') {
    try {
      data = JSON.parse(dataJson);
    } catch (_) {
      data = dataJson; // 解析失败按原字符串
    }
  }

  const xs = signCore(url, data);
  const xt = Date.now().toString();
  return { 'x-s': xs, 'x-t': xt };
}

module.exports = { get_sign };