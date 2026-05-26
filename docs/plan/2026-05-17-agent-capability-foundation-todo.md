# Agent Capability Foundation TODO

Date: 2026-05-17

## Problem

MCP servers, skills, and shared tools are currently surfaced through agent workspaces, but the product model should treat them as one shared capability foundation. Product agents should not each own separate copies of browser, HID, skill, or business tool registration.

## TODO

- Add one global capability foundation management surface for MCP servers, skills, and shared tools.
- Register browser-mcp and VirtualHID once at the foundation layer.
- Expose per-agent capability policy as projection only: visible, disabled, approval required, read-only, write-capable, or blocked.
- Make `JD 同步`, `自动化招聘`, and `AI助手` consume the same registered foundation capabilities through policy filtering.
- Add run-readiness gates so automation cannot start browser/HID work when required MCP servers are missing or unhealthy.
- Show capability health in each agent workspace without duplicating registration controls.
- Keep runtime architecture unified: product agents differ by config, prompt, policy, and run scope, not by separate MCP/tool registries.

## Acceptance Criteria

- browser-mcp and VirtualHID appear once in `/api/mcp/servers`.
- Agent workspaces show the same shared MCP/tool source with agent-specific policy.
- Automation runs that require browser/HID are blocked with a clear missing-capability reason when MCP is not registered.
- MCP/tool/skill registration changes do not require editing each agent separately.
