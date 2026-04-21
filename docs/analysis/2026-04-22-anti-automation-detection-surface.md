# Anti-Automation Detection Surface

**Status**: Analysis
**Date**: 2026-04-22
**Scope**: A complete catalogue of the mechanisms a website (or an embedded anti-bot SDK) can use to detect that the browser is being driven by automation, a debugger, or non-human input. Written as a companion reference to [`docs/draft/2026-04-21-browser-read-and-input-injection-options.md`](../draft/2026-04-21-browser-read-and-input-injection-options.md).

This document is **not** a spec; it is a reference taxonomy. The goal is that whenever a new detection point appears in the wild we can classify it immediately and locate the corresponding mitigation.

---

## 0. How to read this document

Detection mechanisms are organised by **where the signal originates**, not by what tool set is being detected. This is important because the same tool (for example Puppeteer) leaks simultaneously across multiple layers, and the same signal (for example `navigator.webdriver`) can be triggered by several different tools.

For every entry we try to give:

- **Signal** — what the page observes
- **Normal value** — what a real Chrome under a real user would show
- **Anomaly** — what triggers detection
- **Root cause** — who controls it, so the mitigation is unambiguous

A detector in the wild is almost never a single check; it is a **weighted combination** of these signals plus behavioural features plus server-side risk clustering. Passing any single item below does not prove you are undetectable.

---

## 1. Global object / `navigator` / `window` exposure

These are the cheapest and most common checks — a single line of JavaScript.

| Signal | Normal | Anomaly | Root cause |
|---|---|---|---|
| `navigator.webdriver` | `undefined` or `false` | `true` | `--enable-automation`, ChromeDriver, WebDriver BiDi |
| `navigator.plugins.length` | ≥ 3 on desktop Chrome | `0` | Old headless mode |
| `navigator.languages` | non-empty array | `[]` | Old headless mode |
| `navigator.language` | reasonable locale | Disagrees with UA / `Accept-Language` / timezone | Launch flag mismatch |
| `navigator.userAgent` | normal Chrome UA | Contains `HeadlessChrome` | Old headless mode |
| `navigator.platform` | `MacIntel` / `Win32` / `Linux x86_64` / … | Disagrees with UA | UA spoofing without platform sync |
| `navigator.hardwareConcurrency` | 4/8/12/16 | `1`, unusual values, inconsistent with device | Container / VM |
| `navigator.deviceMemory` | 2/4/8 | Inconsistent with `hardwareConcurrency` | Container / VM |
| `navigator.maxTouchPoints` | 0 on desktop, ≥1 on mobile | UA claims iOS but value is `0` | UA spoofing |
| `navigator.connection` | `effectiveType/downlink/rtt` populated | Missing or default | Container |
| `navigator.permissions.query({name:'notifications'})` | `default` | `denied` while `Notification.permission === 'default'` (self-contradictory) | **Classic headless fingerprint** |
| `window.chrome` | present with `runtime` / `loadTimes` / `csi` | `undefined` or shape incomplete | Headless / non-Chromium wrapper |
| `window.chrome.runtime` | real native getters | Shimmed object, wrong `toString` | Stealth patch quality |
| `window.outerWidth` / `outerHeight` | Larger than inner by chrome, tab bar, bookmark bar | equal to inner, or `0` | Headless |
| `window.screenX` / `screenY` | reflects real window position | `0,0` while `innerWidth` is tiny | Headless / odd environment |
| `window.devicePixelRatio` | 1 / 1.5 / 2 / 3 | extreme or fractional values | Odd environment |
| `window.Notification.permission` | `default` | Inconsistent with Permissions API | Headless |

---

## 2. Prototype / native function tampering

Anything the stealth layer overrides leaves a trail.

- `Function.prototype.toString.call(X)` must return `function X() { [native code] }` for any API claimed to be native. Stealth replacements that do not preserve this are detectable.
- `Object.getOwnPropertyDescriptor(navigator, 'webdriver')` reveals whether the property is a plain data descriptor (real Chrome) or a getter installed after the fact (stealth).
- `Reflect.ownKeys(Navigator.prototype)` ordering and count differ after monkey-patching.
- Redefining `Error.prepareStackTrace` or `Error.captureStackTrace` changes the format of `new Error().stack`.
- Installing accessor traps on prototypes is detectable via `Object.getOwnPropertyDescriptor(Proto, key).get.toString()`.

Detection recipe in the wild: iterate over a known list of commonly patched functions (`navigator.plugins`, `Notification.requestPermission`, `chrome.runtime.connect`, `WebGLRenderingContext.prototype.getParameter`, …) and test the two invariants `.toString().includes('[native code]')` and `descriptor.get === undefined || descriptor.get.toString().includes('[native code]')`.

---

## 3. CDP / DevTools Protocol runtime side-channels

Independent of whether the transport is `--remote-debugging-port` or `--remote-debugging-pipe`. What matters is **which CDP domains are enabled**.

### 3.1 The `Runtime.enable` / `Error.stack` getter trap (canonical)

When `Runtime` is enabled, Chrome eagerly formats exceptions (and `console.*` arguments) for the inspector. If the page defines a getter on an `Error`'s `stack` (or on any property read during that serialisation), the getter fires even though the page never reads it.

```js
const e = new Error();
Object.defineProperty(e, 'stack', {
  get() { detected = true; return ''; },
});
console.debug(e); // or let it be thrown
```

No inspector / no `Runtime.enable` → getter never fires. With CDP listening to runtime events → getter fires. This is the most reliable CDP-presence check on the public internet.

### 3.2 `console` argument lazy-expansion

Same mechanism as 3.1: `console.log(someObject)` may trigger lazy expansion of the object when DevTools-like listeners are attached, firing accessors.

### 3.3 `Debugger.enable` JIT downgrade

Enabling the Debugger domain disables a subset of V8 optimisations. Repeated hot loops measured with `performance.now()` show a consistent slowdown.

### 3.4 `debugger;` statement timing

```js
const t = performance.now();
debugger;
if (performance.now() - t > 100) detected = true;
```

Not only actual breakpoints but some attached-inspector states introduce measurable delay.

### 3.5 `Page.addScriptToEvaluateOnNewDocument` ordering

If a stealth patch is not actually installed before the first page script executes (rare, but possible with mis-configured proxies, service workers, or early pre-fetched scripts), the page sees the un-patched values briefly and can snapshot them.

### 3.6 Main-world pollution vs isolated world

Running stealth code in the main world lets the page intercept further patches by overriding `Object.defineProperty`, `Reflect.defineProperty`, getters on `Object.prototype`, etc. Isolated worlds avoid this.

---

## 4. Driver / framework-specific tattoos

The transport is irrelevant here; what matters is whether the automation frameworks themselves were used.

| Source | Typical leaked identifiers |
|---|---|
| ChromeDriver | `window.cdc_adoQpoasnfa76pfcZLmcfl_*`, `window.$cdc_asdjflasutopfhvcZLmcfl_*`, multiple `document.$cdc_*` |
| Selenium | `document.__selenium_unwrapped`, `document.__webdriver_evaluate`, `document.__driver_evaluate`, `window.__webdriver_script_fn` |
| Legacy FxDriver | `document.__fxdriver_unwrapped` |
| Puppeteer / Playwright default launch | `--enable-automation` → `navigator.webdriver=true`; info bar; Permissions/Notification inconsistency |
| Playwright native | Specific UA behaviours; particular launch-flag combinations (`--no-startup-window`, …) |
| `chrome.debugger` extension API | The yellow "DevTools has been attached" notification bar (user-visible) |
| WebDriver BiDi | `navigator.webdriver=true`, BiDi-specific session flags |
| `puppeteer-extra-stealth` (and similar) | Patch imperfections (missing `[native code]`, inconsistent ordering) are themselves fingerprints |

---

## 5. Launch flags / process environment

- `--headless=old` vs `--headless=new`: new headless is close to normal Chrome but still differs in certain codecs and default fonts.
- `--disable-gpu`: WebGL renderer becomes `SwiftShader` / `ANGLE (Google SwiftShader...)`.
- `--no-sandbox`: inferable from certain Permissions API behaviours.
- `--user-data-dir=/tmp/...`: empty profile → no history, no extensions, no logged-in cookies. Sites can detect by probing third-party cookie behaviour, service-worker registration state, etc.
- Leftover `--remote-debugging-port=9222`: an open local port; not reachable from page JS directly, but visible to any other local process.
- Absence of commonly present flags can itself be unusual: a real user Chrome has a recognisable flag profile.

---

## 6. Hardware / graphics / media fingerprints

These tell the server "is this browser shaped like a real user's browser".

1. **WebGL**
   - `WEBGL_debug_renderer_info`: `UNMASKED_VENDOR_WEBGL`, `UNMASKED_RENDERER_WEBGL`.
     - Real: `Apple / Apple M2`, `Google Inc. (NVIDIA) / ANGLE (...)`.
     - Headless / VM: `Google Inc. (Google) / ANGLE (..., SwiftShader ...)`, `Mesa / llvmpipe`.
   - Shader precision ranges, extension list ordering, `getParameter(gl.MAX_*)` combination.
2. **Canvas 2D** — hash of `toDataURL()` after rendering text + shapes. Same GPU + same font stack yields stable hashes; software rasterisers produce characteristic textures.
3. **AudioContext** — hash of FFT output from a fixed oscillator chain (`OscillatorNode → DynamicsCompressor → AnalyserNode`).
4. **Font enumeration** — measure rendered text width in `<canvas>` or offscreen DOM to infer installed fonts. Headless typically has a minimal font set.
5. **Media codecs** — `HTMLMediaElement.canPlayType('video/mp4; codecs="avc1.42E01E"')`, `MediaSource.isTypeSupported(...)`. Headless often returns `""` (empty) instead of `"probably"` for H.264/AAC.
6. **`navigator.mediaDevices.enumerateDevices()`** — real machines enumerate `audioinput`, `audiooutput`, `videoinput`. VMs / headless often return empty or single default entries.
7. **WebRTC / ICE** — STUN discovery exposes local IP. Normal Chrome hides local IPs via mDNS (`*.local`); disabling that feature produces an obviously unusual ICE candidate set.

---

## 7. Environment consistency

Detectors cross-check multiple signals and look for contradictions.

- `screen.{width, height, availWidth, availHeight, colorDepth, pixelDepth}` — must be internally consistent.
- `Intl.DateTimeFormat().resolvedOptions().timeZone` vs IP geolocation.
- `navigator.language` / `navigator.languages` vs `Accept-Language` HTTP header vs IP country.
- `navigator.platform` vs the platform declared in UA.
- UA-CH (`Sec-CH-UA`, `Sec-CH-UA-Platform`, `Sec-CH-UA-Mobile`, `Sec-CH-UA-Full-Version-List`) vs `navigator.userAgent`.
- Feature presence vs the version claimed in UA (a real Chrome 130 supports a specific API set).

Any inconsistency is a high-confidence automation signal.

---

## 8. Behavioural signals (the hardest to forge)

### 8.1 Event properties

- `event.isTrusted === false` for every synthetic event (CDP `Input.dispatchMouseEvent`, JS `dispatchEvent`, parts of `element.click()`). Real hardware and `CGEventPostToPid` / virtual HID produce `true`.
- `MouseEvent.sourceCapabilities` is `null` on some synthetic paths.
- `event.detail`, `event.which`, `event.buttons` consistency.
- `event.screenX/Y` vs `clientX/Y` must match the actual window on-screen position.
- `PointerEvent.pointerType`: `'mouse'` for desktop, `'touch'` for mobile, `'pen'` for stylus. UA claiming mobile but always `'mouse'` is suspicious.
- `PointerEvent.pressure`: real stylus / touch produces continuous 0.0–1.0; synthetic is usually 0 or a constant 0.5.

### 8.2 Mouse trajectory and timing

- Straight-line or teleport-to-button motion without a `mousemove` stream.
- No `mouseover` / `mouseenter` / `mousemove` run-up before `click`.
- `mousedown` → `mouseup` interval fixed to the millisecond (humans jitter 40–150 ms).
- Consecutive click cadence exactly regular (humans follow lognormal / exponential distributions).
- Click coordinates always exactly at the geometric centre of the target (real users disperse, typically biased off-centre).
- `mousemove` sampling rate too low (synthetic ~60 Hz) or too high.
- Bézier curves that look "too clean" without micro-jitter.

### 8.3 Keyboard

- Required event order `keydown` → `keypress` (where applicable) → `input` → `keyup` and their relative timings.
- Fixed inter-key intervals.
- Missing IME composition events (`compositionstart` / `compositionupdate` / `compositionend`) in CJK contexts where a human would produce them.
- Setting `element.value = "..."` directly with no keyboard events and no `input` event at all.

### 8.4 Scroll

- `WheelEvent.deltaX/Y/Z`, `deltaMode` shapes: macOS trackpads produce continuous small deltas plus inertia; mouse wheels step in integers.
- Instantaneous scrolling with no deceleration.

### 8.5 Macro-level

- Clicking instantly after navigation (humans need 200–800 ms to scan).
- Overall dwell time too short or too regular.
- Visit order is strictly DFS / BFS.
- No hover exploration — mouse jumps directly to targets.
- Triggering honeypot links or hidden form fields that a real user cannot see.
- Maintaining a long session without ever touching `document.cookie` / `localStorage`.

---

## 9. Network-layer fingerprints

Independent of JS but increasingly used.

| Layer | Fingerprint |
|---|---|
| TLS | JA3 / JA4 (cipher suites, extension order, ALPN). Launching real Chrome gives you real-Chrome TLS fingerprints. Issuing requests from Node/Python does not. |
| HTTP/2 | SETTINGS frame order, WINDOW_UPDATE timing, pseudo-header order (`:method`, `:authority`, `:scheme`, `:path`). |
| HTTP/3 / QUIC | Transport parameter order. |
| HTTP headers | Header ordering, casing, presence of `sec-fetch-*`, `Accept-Encoding` containing `br`/`zstd`, `Accept-Language` consistent with `navigator.languages`. |
| Cookies | Expected third-party cookies present; SameSite behaviour matches Chrome's current rules. |
| IP | Datacenter ASN vs residential; geolocation consistent with declared timezone. |

---

## 10. Honeypots and consistency traps (server-planted)

- **Hidden fields / links**: `display:none`, `visibility:hidden`, `opacity:0`, `position:absolute;left:-9999px`, zero-dimension, `aria-hidden="true"` on interactive elements.
- **Inverse captcha**: a checkbox pre-checked as "I am a robot"; humans uncheck it.
- **`pointer-events:none` decoy buttons**.
- **Timing trap**: form submission within N ms of field focus → bot.
- **Invisible captchas**: reCAPTCHA v3, Cloudflare Turnstile, hCaptcha Invisible emit a continuous 0–1 behavioural score.
- **DOM mutation probes**: inject an element with a delayed render and observe whether the client interacts with it prematurely.

---

## 11. Extension / injected-script exposure

Even if we are not using extensions, other detectors assume some adversaries do; and we should know exactly what each path exposes.

- `web_accessible_resources` enumeration: `fetch('chrome-extension://<id>/manifest.json')` success.
- Content script residue: extra `<script>` / `<style>`, DOM attributes, class names, `data-*`.
- `postMessage` bridges: observable `MessageEvent.origin` / `source`.
- Extra properties attached to `window` or `document`.
- Custom event names (`dispatchEvent(new CustomEvent('myext_*'))`).
- Timing: unexpected script execution around `DOMContentLoaded`.
- Service Worker registered by an extension.
- Inside iframes: whether `window.chrome.runtime.id` resolves.

---

## 12. Timing / precision side-channels

- `performance.now()` precision: normal Chrome 100 µs; some debugger configurations differ.
- Delta between `Date.now()` and `performance.timeOrigin`.
- `requestAnimationFrame` frequency: a real backgrounded tab throttles to 1 Hz. If you fake `document.hasFocus()` to `true` via `setFocusEmulationEnabled` but leave `document.visibilityState === 'hidden'`, the rAF frequency may not match either state.
- `requestIdleCallback` deadline distribution.
- `setTimeout(fn, 0)` clamp (~4 ms in Chrome).
- Microtask vs macrotask ordering differences under some runtimes.
- `SharedArrayBuffer` + `Atomics.wait` high-precision timing (requires COOP / COEP).

---

## 13. Headless-specific legacy leaks

Even the new headless mode is much closer to normal Chrome, but a few signals persist:

- `navigator.plugins.length === 0` (old headless).
- `navigator.languages === []` (old headless).
- `window.chrome` missing (old headless).
- `Notification.permission === 'denied'` with no prior request.
- The Notification/Permissions triple inconsistency (see §1).
- `canPlayType` returning `""` instead of `"probably"`.
- WebGL renderer containing `SwiftShader`.
- Very small installed font set.

---

## 14. Machine-learning signals (server-side aggregation)

Not a single JS check, but worth listing because the final decision is almost always ML-on-top:

- LSTM / CNN classification on mouse trajectory sequences.
- Keystroke-dynamics authentication.
- Time-series features over dwell, navigation depth, click cadence.
- Cross-session device identification via (canvas + WebGL + audio + font + UA-CH) hash clustering.
- Account linkage through shared IP / fingerprint / behavioural signatures.

Implication for our design: **no single mitigation is proof of invisibility**. Modern anti-bot is a multi-signal vote plus ML scoring plus risk thresholds.

---

## 15. Mapping to `recruit-agent`'s current choices

| Capability we need | Dominant detection points |
|---|---|
| Read DOM without being observed | §3.1 `Runtime.enable` side-channel; §2 native-function tampering; §3.6 isolated-world hygiene |
| Human-like clicks | §8.1 `isTrusted`; §8.2 trajectory; run-up events; `mousedown`/`mouseup` distribution; `PointerEvent.pointerType/pressure`; off-centre landing |
| Stay active in background | §1 `document.hasFocus()`, `document.visibilityState`, `document.hidden`; §12 rAF throttling; Page Lifecycle state |
| Not expose "automation" | §1 `navigator.webdriver`; §4 info bar; `--enable-automation`; §3 CDP domain hygiene; `cdc_` / `__webdriver_*` residues; UA containing `HeadlessChrome` |

The direct consequence for the two-tier plan in [`docs/draft/2026-04-21-browser-read-and-input-injection-options.md`](../draft/2026-04-21-browser-read-and-input-injection-options.md):

- Tier one (`--remote-debugging-pipe` + `CGEventPostToPid`) already covers §1 (by not passing `--enable-automation`), §4 (by not using ChromeDriver / the debugger extension), and is acceptable for §8.1 (since `CGEventPostToPid` produces `isTrusted=true`). Ongoing risk concentrates in §3 (keep CDP domain surface minimal), §8.2/§8.3 (the humanisation layer), and §14 (the ML aggregation we cannot enumerate).
- Tier two (virtual HID + custom Chromium private read channel) eliminates §3 and §8.1 entirely by construction; §2 disappears because there is no stealth patching. The residual surface reduces to §6 / §7 / §9 / §10 / §14, which are platform- / network- / server-side topics rather than automation signals.

---

## 16. Operating rules for this document

1. Every new detection point observed in the wild must be added under the matching section above, with the four fields (signal, normal, anomaly, root cause).
2. If a new point cannot be mapped to any existing section, a new section is added; do not pollute the global object section with, say, a TLS signal.
3. Mitigations are intentionally **not** written here. Mitigations depend on the chosen architecture and belong in the strategy / plan documents that reference this catalogue.
4. This document describes **what the page can observe**. It deliberately excludes server-side behavioural clustering black boxes that are neither observable nor directly countered at the browser layer; those belong in the risk-model document, not here.
