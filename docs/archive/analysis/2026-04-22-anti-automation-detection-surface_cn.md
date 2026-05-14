# 反自动化检测面清单

**状态**: 分析
**日期**: 2026-04-22
**范围**: 完整梳理网站（或其嵌入的反爬 SDK）可以用来判定浏览器正在被自动化驱动、被调试或存在非真人输入的检测机制，作为 [`docs/draft/2026-04-21-browser-read-and-input-injection-options.md`](../draft/2026-04-21-browser-read-and-input-injection-options.md) 的配套参考。

本文件**不是**规范，而是一份分类参考。目标是：当有新的检测点出现时，能立刻归类并找到对应的规避手段。

---

## 0. 阅读说明

检测机制按"**信号从哪里产生**"分层，而不是按"正在检测哪种工具"。原因：同一个工具（如 Puppeteer）会同时在多层泄露；同一个信号（如 `navigator.webdriver`）也会被多种工具触发。

每一项尽量给出：

- **信号**：页面能观测到什么
- **正常值**：真实用户的 Chrome 会长什么样
- **异常情况**：什么触发检测
- **根因**：谁控制它，以便规避手段不产生歧义

线上的反爬几乎从不依赖单一检测，而是**多信号加权** + 行为特征 + 服务端风险聚类。**通过下面任何一条都不等于"隐身"**。

---

## 一、全局对象 / `navigator` / `window` 暴露面

最便宜、最常见的检测，一行 JS 就能读。

| 信号 | 正常值 | 异常情况 | 根因 |
|---|---|---|---|
| `navigator.webdriver` | `undefined` 或 `false` | `true` | `--enable-automation`、ChromeDriver、WebDriver BiDi |
| `navigator.plugins.length` | 桌面 Chrome ≥ 3 | `0` | 老 headless 模式 |
| `navigator.languages` | 非空数组 | `[]` | 老 headless 模式 |
| `navigator.language` | 合理本地化值 | 与 UA / `Accept-Language` / 时区不匹配 | 启动参数不同步 |
| `navigator.userAgent` | 正常 Chrome UA | 含 `HeadlessChrome` | 老 headless 模式 |
| `navigator.platform` | `MacIntel` / `Win32` / `Linux x86_64` 等 | 与 UA 声明的平台不一致 | UA 伪造未同步改 platform |
| `navigator.hardwareConcurrency` | 4 / 8 / 12 / 16 | `1` 或奇异值，与设备不匹配 | 容器 / 虚拟机 |
| `navigator.deviceMemory` | 2 / 4 / 8 | 与 `hardwareConcurrency` 极不协调 | 容器 / 虚拟机 |
| `navigator.maxTouchPoints` | 桌面 0 / 移动 ≥ 1 | UA 声明 iOS 但值为 `0` | UA 伪造 |
| `navigator.connection` | `effectiveType/downlink/rtt` 有值 | 缺失或全为默认 | 容器 |
| `navigator.permissions.query({name:'notifications'})` | `default` | `denied` 同时 `Notification.permission === 'default'`（自相矛盾） | **经典 headless 指纹** |
| `window.chrome` | 存在，有 `runtime` / `loadTimes` / `csi` | `undefined` 或结构残缺 | headless / 非 Chromium 壳 |
| `window.chrome.runtime` | 真实的 native getter | 被 shim 过、`toString` 不对 | stealth 补丁质量 |
| `window.outerWidth` / `outerHeight` | 比 inner 大，含任务栏 / 书签栏 | 等于 inner 或为 `0` | headless |
| `window.screenX` / `screenY` | 反映真实窗口屏内位置 | `0,0` 但 innerWidth 明显偏小 | headless / 异常环境 |
| `window.devicePixelRatio` | 1 / 1.5 / 2 / 3 | 极端或罕见分数 | 异常环境 |
| `window.Notification.permission` | `default` | 与 Permissions API 返回不一致 | headless |

---

## 二、原型链 / native 函数被改写的痕迹

凡是 stealth 层覆写过的，都会留下尾巴。

- `Function.prototype.toString.call(X)` 对声称是 native 的 API 必须返回 `function X() { [native code] }`。stealth 替换若不保持这一点即可检出。
- `Object.getOwnPropertyDescriptor(navigator, 'webdriver')` 能区分：真实 Chrome 是数据描述符；stealth 往往是事后装上的 getter。
- `Reflect.ownKeys(Navigator.prototype)` 的顺序与数量在 monkey-patch 后会变。
- 改写 `Error.prepareStackTrace` / `Error.captureStackTrace` 会改变 `new Error().stack` 格式。
- 装在原型上的 accessor 陷阱可通过 `Object.getOwnPropertyDescriptor(Proto, key).get.toString()` 反查。

**线上套路**：遍历一批常被补的函数（`navigator.plugins`、`Notification.requestPermission`、`chrome.runtime.connect`、`WebGLRenderingContext.prototype.getParameter` …），挨个校验两条不变式 `.toString().includes('[native code]')` 与 `descriptor.get === undefined || descriptor.get.toString().includes('[native code]')`。

---

## 三、CDP / DevTools 协议运行时侧信道

**与传输是 `--remote-debugging-port` 还是 `--remote-debugging-pipe` 无关**，关键是**启用了哪些 CDP domain**。

### 3.1 `Runtime.enable` 的 `Error.stack` getter 陷阱（经典）

`Runtime` 启用后，Chrome 会急切地把异常和 `console.*` 参数序列化给 inspector。如果页面在 `Error` 的 `stack`（或序列化过程访问到的某个属性）上装了 getter，该 getter 会被触发，即使页面根本没读它。

```js
const e = new Error();
Object.defineProperty(e, 'stack', {
  get() { detected = true; return ''; },
});
console.debug(e); // 或让它被抛出
```

无 inspector / 无 `Runtime.enable` → getter 不会触发。  
有 CDP 监听 runtime 事件 → getter 触发。  
这是公开网络上最可靠的 CDP 在场检测。

### 3.2 `console` 参数懒展开

和 3.1 同机制：`console.log(someObject)` 在有 DevTools 类监听时会触发对象的懒展开，从而命中 accessor。

### 3.3 `Debugger.enable` JIT 降级

开启 Debugger domain 会关掉 V8 一部分优化。用 `performance.now()` 测量热点循环能观测到稳定的慢速。

### 3.4 `debugger;` 语句时序

```js
const t = performance.now();
debugger;
if (performance.now() - t > 100) detected = true;
```

不只是真断点，某些 inspector 附着状态也会带来可测时延。

### 3.5 `Page.addScriptToEvaluateOnNewDocument` 注入时机

如果 stealth 补丁没能在页面首段脚本前装上（少见，但配置错的代理、SW、早期预取脚本都可能造成），页面会在短暂窗口读到未打补丁的值并留快照。

### 3.6 主 world 污染 vs isolated world

stealth 代码跑在主 world 时，页面可以通过覆写 `Object.defineProperty` / `Reflect.defineProperty` / `Object.prototype` 上的 getter 来反向嗅探后续补丁。isolated world 可规避。

---

## 四、驱动 / 框架特有的"纹身"

传输无关，取决于**是否用了这些自动化框架**。

| 来源 | 典型泄漏标识 |
|---|---|
| ChromeDriver | `window.cdc_adoQpoasnfa76pfcZLmcfl_*`、`window.$cdc_asdjflasutopfhvcZLmcfl_*`、多处 `document.$cdc_*` |
| Selenium | `document.__selenium_unwrapped`、`document.__webdriver_evaluate`、`document.__driver_evaluate`、`window.__webdriver_script_fn` |
| 老 FxDriver | `document.__fxdriver_unwrapped` |
| Puppeteer / Playwright 默认启动 | `--enable-automation` → `navigator.webdriver=true`；信息栏；Notification/Permissions 不一致 |
| Playwright 原生 | 特定 UA 行为、特定启动参数组合（`--no-startup-window` 等） |
| `chrome.debugger` 扩展 API | "DevTools 已附着" 黄色通知栏（用户可见） |
| WebDriver BiDi | `navigator.webdriver=true`、BiDi 特有 session 标志 |
| `puppeteer-extra-stealth` 等 | 补丁本身的不完美（缺 `[native code]`、顺序不对）即是指纹 |

---

## 五、启动参数 / 进程环境

- `--headless=old` vs `--headless=new`：新 headless 已接近普通 Chrome，但 codec、默认字体仍有差异。
- `--disable-gpu`：WebGL renderer 变成 `SwiftShader` / `ANGLE (Google SwiftShader...)`。
- `--no-sandbox`：可通过某些 Permissions API 行为推断。
- `--user-data-dir=/tmp/...`：空档案 → 无历史、无扩展、无登录 cookie。站点可通过第三方 cookie、SW 注册状态等行为识别。
- 残留 `--remote-debugging-port=9222`：本机开放端口，页面 JS 不能直接访问，但任何本机进程可见。
- 常见参数缺失本身就异常：真实 Chrome 有一组可识别的 flag profile。

---

## 六、硬件 / 图形 / 媒体指纹

用于判断"这个浏览器长得是不是真实用户"。

1. **WebGL**
   - `WEBGL_debug_renderer_info` 的 `UNMASKED_VENDOR_WEBGL` / `UNMASKED_RENDERER_WEBGL`：
     - 真实：`Apple / Apple M2`、`Google Inc. (NVIDIA) / ANGLE (...)`。
     - headless / VM：`Google Inc. (Google) / ANGLE (..., SwiftShader ...)`、`Mesa / llvmpipe`。
   - shader precision、扩展列表顺序、`getParameter(gl.MAX_*)` 组合。
2. **Canvas 2D** —— 绘制文字 + 图形后 `toDataURL()` 的 hash。同 GPU + 同字体栈 hash 稳定；软件光栅有特征纹理。
3. **AudioContext** —— 固定振荡器链路 (`OscillatorNode → DynamicsCompressor → AnalyserNode`) 的 FFT hash。
4. **字体枚举** —— 在 `<canvas>` 或离屏 DOM 测量文本宽度反推安装字体。headless 字体极少。
5. **媒体 codec** —— `canPlayType('video/mp4; codecs="avc1.42E01E"')`、`MediaSource.isTypeSupported(...)`。headless 对 H.264 / AAC 经常返回 `""` 而不是 `"probably"`。
6. **`navigator.mediaDevices.enumerateDevices()`** —— 真实机器枚举出 `audioinput` / `audiooutput` / `videoinput`。VM / headless 常返回空或只有 default 项。
7. **WebRTC / ICE** —— STUN 探测本地 IP。正常 Chrome 通过 mDNS (`*.local`) 隐藏本地 IP；关掉该特性反而暴露。

---

## 七、环境一致性

检测器会交叉对比多路信号，寻找矛盾：

- `screen.{width, height, availWidth, availHeight, colorDepth, pixelDepth}` 内部自洽。
- `Intl.DateTimeFormat().resolvedOptions().timeZone` vs IP 地理位置。
- `navigator.language` / `languages` vs `Accept-Language` HTTP 头 vs IP 国家。
- `navigator.platform` vs UA 声明的平台。
- UA-CH（`Sec-CH-UA`、`Sec-CH-UA-Platform`、`Sec-CH-UA-Mobile`、`Sec-CH-UA-Full-Version-List`）vs `navigator.userAgent`。
- 特性存在性 vs UA 声称的 Chrome 版本（每个真实 Chrome 版本有一组已知 API 集）。

**任何一处不一致**即是高置信度的自动化信号。

---

## 八、行为级信号（最难伪造）

### 8.1 事件属性

- `event.isTrusted === false`：所有合成事件（CDP `Input.dispatchMouseEvent`、JS `dispatchEvent`、`element.click()` 的一部分）都会是 `false`。真实硬件、`CGEventPostToPid`、虚拟 HID 产生 `true`。
- `MouseEvent.sourceCapabilities`：某些合成路径为 `null`。
- `event.detail`、`event.which`、`event.buttons` 一致性。
- `event.screenX/Y` vs `clientX/Y` 必须与窗口真实屏内位置匹配。
- `PointerEvent.pointerType`：桌面 `'mouse'`、移动 `'touch'`、笔 `'pen'`。UA 声称移动但永远是 `'mouse'` 即异常。
- `PointerEvent.pressure`：真实触控笔 / 触屏为连续 0.0–1.0；合成常为 0 或固定 0.5。

### 8.2 鼠标轨迹与时序

- 完全直线或瞬移到按钮，无 `mousemove` 流。
- 点击前无 `mouseover` / `mouseenter` / `mousemove` 前摇。
- `mousedown` → `mouseup` 间隔固定到毫秒（真人 40–150 ms 抖动）。
- 连续点击节奏完全规律（真人遵循 lognormal / exponential 分布）。
- 点击坐标总是精准落在元素几何中心（真人离散，往往偏离中心）。
- `mousemove` 采样频率过低（合成常 60 Hz）或过高。
- 贝塞尔曲线"过于干净"，无微抖。

### 8.3 键盘

- 事件顺序 `keydown` → `keypress`（适用时）→ `input` → `keyup` 及其相对时延。
- 每键间隔固定。
- CJK 场景应出现的 IME 组合事件（`compositionstart/update/end`）缺失。
- 直接 `element.value = "..."`，既无键盘事件也无 `input` 事件。

### 8.4 滚动

- `WheelEvent.deltaX/Y/Z`、`deltaMode`：macOS 触控板是连续小 delta + 惯性尾巴；鼠标滚轮是整数阶跃。
- 瞬时滚动到位，无减速曲线。

### 8.5 宏观行为

- 导航完立刻点击（真人需 200–800 ms 扫视）。
- 整体停留时间过短或过规律。
- 访问顺序严格 DFS / BFS。
- 无 hover 探索，鼠标直扑目标。
- 触发蜜罐链接或隐藏表单（真人看不见的）。
- 长会话期间从不触碰 `document.cookie` / `localStorage`。

---

## 九、网络层指纹

与 JS 无关，但近年被反爬越来越多使用。

| 层 | 指纹 |
|---|---|
| TLS | JA3 / JA4（cipher suites、extension 顺序、ALPN）。拉真 Chrome 得真 Chrome TLS 指纹；Node/Python 里自己发请求会露馅 |
| HTTP/2 | SETTINGS 帧顺序、WINDOW_UPDATE 时序、伪头顺序（`:method` `:authority` `:scheme` `:path`） |
| HTTP/3 / QUIC | transport parameter 顺序 |
| HTTP 头 | 头顺序、大小写、`sec-fetch-*` 是否齐全、`Accept-Encoding` 是否含 `br`/`zstd`、`Accept-Language` 与 `navigator.languages` 一致 |
| Cookie | 预期第三方 cookie 是否携带；SameSite 行为是否符合 Chrome 当前规则 |
| IP | 数据中心 ASN vs 住宅；地理位置与声明时区一致性 |

---

## 十、蜜罐与一致性陷阱（服务端埋）

- **隐藏字段 / 链接**：`display:none`、`visibility:hidden`、`opacity:0`、`position:absolute;left:-9999px`、零尺寸、交互元素上的 `aria-hidden="true"`。
- **反向验证码**：一个预勾 "我是机器人" 的 checkbox，真人会取消。
- **`pointer-events:none` 的诱饵按钮**。
- **时序陷阱**：表单字段聚焦到提交 < N ms → 判为 bot。
- **隐形验证码**：reCAPTCHA v3、Cloudflare Turnstile、hCaptcha Invisible 输出 0–1 连续行为评分。
- **DOM mutation 探针**：注入一个延迟渲染的元素，观察客户端是否"提前"交互。

---

## 十一、扩展 / 注入脚本暴露面

即使我们不用扩展，也要知道这些路径暴露什么，便于识别对手。

- `web_accessible_resources` 枚举：`fetch('chrome-extension://<id>/manifest.json')` 是否成功。
- content script 残留：多出的 `<script>` / `<style>`、DOM 属性、class、`data-*`。
- `postMessage` 桥：可观测的 `MessageEvent.origin` / `source`。
- 附加在 `window` / `document` 上的属性。
- 自定义事件名 (`dispatchEvent(new CustomEvent('myext_*'))`)。
- 时序：`DOMContentLoaded` 前后的陌生脚本执行。
- 扩展注册的 Service Worker。
- iframe 内 `window.chrome.runtime.id` 能否解析。

---

## 十二、时序 / 精度侧信道

- `performance.now()` 精度：正常 Chrome 100 µs；某些调试配置不同。
- `Date.now()` 与 `performance.timeOrigin` 差值。
- `requestAnimationFrame` 频率：真实后台 tab 节流到 1 Hz。若用 `setFocusEmulationEnabled` 假装 `hasFocus=true` 但 `visibilityState` 仍为 `hidden`，rAF 频率就无法同时匹配两个状态。
- `requestIdleCallback` deadline 分布。
- `setTimeout(fn, 0)` clamp（Chrome 约 4 ms）。
- 某些运行时下 microtask vs macrotask 顺序差异。
- `SharedArrayBuffer` + `Atomics.wait` 高精度时序（需 COOP / COEP）。

---

## 十三、Headless 遗留特征

新 headless 已接近普通 Chrome，但仍有少量信号：

- `navigator.plugins.length === 0`（老 headless）。
- `navigator.languages === []`（老 headless）。
- `window.chrome` 缺失（老 headless）。
- `Notification.permission === 'denied'` 但从未请求过。
- Notification/Permissions 三元不一致（见 §一）。
- `canPlayType` 返回 `""` 而非 `"probably"`。
- WebGL renderer 含 `SwiftShader`。
- 安装字体极少。

---

## 十四、机器学习级信号（服务端聚合）

不是单条 JS 能看到的，但最终判定几乎总是 ML 叠加，列出以便设计时知道这是最后一道：

- 鼠标轨迹序列的 LSTM / CNN 分类。
- 按键节奏 keystroke dynamics 鉴权。
- 停留、导航深度、点击节奏的时间序列特征。
- （canvas + WebGL + audio + font + UA-CH）hash 聚类做跨会话设备识别。
- 通过共享 IP / 指纹 / 行为签名做账号关联。

**对设计的含义**：任何单项规避都不是隐身证明。现代反爬 = 多信号投票 + ML 打分 + 风控阈值。

---

## 十五、对 `recruit-station` 当前选型的映射

| 所需能力 | 主要对应检测点 |
|---|---|
| 读 DOM 不被感知 | §3.1 `Runtime.enable` 侧信道；§二 native 函数改写；§3.6 isolated world 卫生 |
| 拟人点击 | §8.1 `isTrusted`；§8.2 轨迹；前摇事件链；`mousedown`/`mouseup` 分布；`PointerEvent.pointerType/pressure`；落点偏中心 |
| 后台不失活 | §一 `document.hasFocus()` / `visibilityState` / `hidden`；§十二 rAF 节流；Page Lifecycle 状态 |
| 不暴露"自动化" | §一 `navigator.webdriver`；§四 信息栏；`--enable-automation`；§三 CDP domain 卫生；`cdc_` / `__webdriver_*` 残留；UA 含 `HeadlessChrome` |

对 [`docs/draft/2026-04-21-browser-read-and-input-injection-options.md`](../draft/2026-04-21-browser-read-and-input-injection-options.md) 中两档方案的直接结论：

- **档位一**（`--remote-debugging-pipe` + `CGEventPostToPid`）已覆盖 §一（不传 `--enable-automation`）、§四（不用 ChromeDriver / 调试扩展），并满足 §8.1（`CGEventPostToPid` 产出 `isTrusted=true`）。剩余风险集中在 §三（CDP domain 要最小化）、§8.2/§8.3（拟人层）、§十四（我们无法枚举的 ML 聚合）。
- **档位二**（虚拟 HID + 定制 Chromium 私有读通道）从架构上消灭 §三与 §8.1；§二也消失，因为不再需要 stealth 补丁。剩余只剩 §六 / §七 / §九 / §十 / §十四，均为平台 / 网络 / 服务端议题，而非自动化信号。

---

## 十六、本文档的维护规则

1. 任何新观测到的检测点必须归入上述章节，并补齐四项字段（信号、正常值、异常情况、根因）。
2. 新检测点若无法映射到现有章节，则新增章节；**不**把 TLS 类信号塞进全局对象章节。
3. 本文**不**写规避手段。规避取决于具体架构选型，归入引用本清单的策略 / 计划文档。
4. 本文只描述**页面可观测**的内容。服务端的行为聚类黑盒既不可直接观测也不能在浏览器层对抗，归入风控模型文档，不在本文。
