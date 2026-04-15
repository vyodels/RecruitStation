# Session Handoff 2026-04-15

## 当前状态

本次会话已经把主执行链彻底切到 **E 模式**：

- `GoalSpec -> AgentRun -> adaptive stage -> ExecutionTrace / StrategyFragment / ExecutionGraphProjection`
- 旧 `workflow` 运行主链已经移除
- 存储层也已切到 `Playbook / Blueprint`
- Boss 平台硬编码动作、Browser MCP 唯一桥接、mock/fallback 伪执行都已移除
- runtime 现在只消费 **真实外部能力**，主要通过 **MCP 注册 + 动态工具注册**

当前分支状态：

- 分支：`main`
- 相对远端：`ahead 8`

最近提交：

- `2298b53` `chore: remove obsolete workflow files`
- `80dd5c2` `refactor: cut storage over to playbooks`
- `5814d1a` `feat: fully cut runtime over to adaptive goals`
- `1eabb2b` `feat: cut runtime over to goal-driven execution`
- `c77233b` `feat: add mcp registry and real environment runtime`
- `9abd27e` `feat: add adaptive runtime goals and operator interactions`
- `99db4a0` `feat: recover interrupted runtime tasks after restart`
- `e7aee44` `feat: finalize recruit agent runtime baseline`

## 本次会话实际验证到哪里

已完成：

- 前端开发页可启动并正常渲染
- 后端可启动并通过健康检查
- 主功能区已做基础 smoke test：
  - `概览`
  - `Agent IM`
  - `招聘 Agent`
  - `工作台`
  - `自学习/演进`
  - `设置`
- 设置页里的 MCP 管理区可正常工作
- 已通过 UI 安装 `Browser MCP` 预置模板

当前阻塞点：

- `Browser MCP` 预置模板安装后，健康检查为 `unhealthy`
- 原因是本机没有真正运行一个兼容的 Browser MCP socket 服务
- 当前报错是：
  - `MCP socket not found: .../browser-mcp.sock`

这意味着：

- 页面和后端主流程基本正常
- **真实网页读取/操作尚未真正打通**
- 下一步必须先让真实 Browser MCP 跑起来，才能继续测试 `zhipin.com`

## 换电脑后继续的最短路径

### 1. 启动项目

前端：

```bash
npm --workspace apps/desktop run dev
```

后端：

```bash
cd services/backend
python3 -m uvicorn scene_pilot.server:create_app --factory --host 127.0.0.1 --port 8741
```

访问：

- 前端：`http://localhost:5174/`
- 后端健康检查：`http://127.0.0.1:8741/health`

### 2. 先确认这些页面能打开

- `概览`
- `Agent IM`
- `招聘 Agent`
- `工作台`
- `自学习/演进`
- `设置`

### 3. 进入设置页

需要做两件事：

- 配置 provider 的 `host / api key / model`
- 配置并启用可用的 MCP，尤其是 Browser MCP

注意：

- API key 没有写进仓库文档
- 换电脑后需要重新本地输入

### 4. 让 Browser MCP 真正可用

只有 Browser MCP 健康检查通过后，才适合继续测试 `zhipin.com`。

当前项目里的 Browser MCP 只是一个**预置模板**，不是现成运行中的服务。它要求外部有一个兼容的本地 socket 服务存在，默认路径类似：

- `/tmp/browser-mcp.sock`
- 或环境变量 `MCP_BROWSER_CHROME_SOCKET` 指向的路径

### 5. 再进入真实招聘试验

第一阶段目标仍是：

- 通过软件本身完成对 `zhipin.com` 的真实读取
- 先拿到候选人的信息

## Browser MCP 的来源

这次用到的 `Browser MCP` 不是从某个现成可用 npm 包“装出来”的成品。

当前项目里的来源是：

- 后端内置了一个 **MCP 预置模板**
- 位置：`services/backend/src/scene_pilot/services/mcp_registry.py`
- 关键常量：`BROWSER_SOCKET_PRESET_KEY = "browser-json-socket"`

这个预置模板会注册一组**通用浏览器工具**：

- `browser_list_tabs`
- `browser_snapshot`
- `browser_execute_script`

它走的是：

- `unix_socket`
- 协议：`json_socket_browser_command`

也就是说：

- 现在的 Browser MCP 是**项目内定义的预置接入模板**
- 不是 Boss 专用代码
- 也不是 runtime 写死的唯一桥
- 但它仍然依赖一个外部真实 socket 服务来承接调用

补充说明：

- 会话里我确实额外看过 npm 上是否有现成 `browser-mcp` 包
- 结果发现同名包基本不可用，不是当前项目依赖的正式来源
- **当前代码并不依赖那个 npm 包**

## 当前本地运行数据

这次会话结束时，本地仍存在运行数据库：

- `data/recruit-agent.db`
- `services/backend/data/recruit-agent.db`

这些文件：

- 不应提交进仓库
- 但如果你希望把**本地运行态、历史记录、会话数据**一起带到新电脑，可以手动拷走

如果只想延续“开发进度和当前判断”，文档就够了。  
如果还想延续“本地 agent 历史和数据库状态”，需要连这两个 SQLite 文件一起迁走。

## 下一步建议

优先顺序：

1. 在新电脑上拉起前后端
2. 重新填写 provider 配置
3. 跑起真实 Browser MCP
4. 健康检查通过后，打开 `zhipin.com`
5. 从 `工作台` 或目标驱动入口，跑第一阶段目标：拿到候选人信息

## 相关文档

- [Plan.md](../Plan.md)
- [docs/project-handoff.md](./project-handoff.md)
- [docs/runtime-and-hermes-comparison.md](./runtime-and-hermes-comparison.md)
- [docs/recruit-agent-web-tooling-notes.md](./recruit-agent-web-tooling-notes.md)
