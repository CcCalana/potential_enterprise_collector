// 小红书官网 `_nuxt/*.js` 中截取的核心签名函数 seccore_signv2
// 注意：此文件来自浏览器打包代码，体积可能较大，也可能依赖 window / document 等浏览器 API。
// 如需在 Node 环境中运行，可在执行前：
//   global.window = global;
// 并为所需属性打桩（stub）或引入 polyfill。
// 下列代码仅为示例；请根据实际抓取到的完整版脚本替换。

// 让浏览器脚本在 Node 环境可用
if (typeof global.window === 'undefined') global.window = global;
if (typeof global.self === 'undefined') global.self   = global;
if (typeof global.document === 'undefined') global.document = {};

/**
 * 小红书 seccore_signv2 核心签名函数
 * @param {string} e - 请求 URL
 * @param {object|string} a - 请求数据（对象或字符串）
 * @returns {string} - 生成的签名字符串
 */
function seccore_signv2(e, a) {
    var r = window.toString;
    var c = e;

    // 判断 a 的类型，拼接参数
    if (
        r.call(a) === "[object Object]" ||
        r.call(a) === "[object Array]" ||
        ((typeof a === "undefined" ? "undefined" : (0, h._)(a)) === "object" && a !== null)
    ) {
        c += JSON.stringify(a);
    } else if (typeof a === "string") {
        c += a;
    }

    // 生成摘要
    var d = (0, p.Pu)([c].join(""));
    // 生成 mnsv2 签名
    var f = window.mnsv2(c, d);

    // 构造签名参数对象
    var s = {
        x0: u.i8,
        x1: "xhs-pc-web",
        x2: window[u.mj] || "PC",
        x3: f,
        x4: a ? (typeof a === "undefined" ? "undefined" : (0, h._)(a)) : ""
    };

    // 返回最终签名
    return "XYS_" + (0, p.xE)((0, p.lz)(JSON.stringify(s)));
}

// 确保先执行整包脚本（里面会把依赖都注册到 window）
require('./vendor-dynamic.4f7b1174.js');

// 有些 Nuxt 包会把 seccore_signv2 挂到 window，下列名字常见
const signFn =
  window.seccore_signv2 ||
  window._seccore_signv2 ||
  window._webmsxyw ||      // 也可能是这个
  null;

if (!signFn) {
  throw new Error('在 vendor-dynamic 文件里没找到 seccore_signv2，请再确认函数名');
}

function get_sign(url, dataJson = '', cookie = '') {
  let data = '';
  if (dataJson && dataJson.trim()) {
    try { data = JSON.parse(dataJson); } catch { data = dataJson; }
  }
  const xs = signFn(url, data);
  return { 'x-s': xs, 'x-t': Date.now().toString() };
}

module.exports = { get_sign };
