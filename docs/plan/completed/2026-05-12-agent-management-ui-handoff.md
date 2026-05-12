# Agent Management UI Handoff

Date: 2026-05-12
Branch: `main`

## Scope

This pass redesigns Agent Management as a regular workspace page instead of a floating overlay, and aligns the runtime conversation surface with the compact management UI reference.

The change is intentionally a UI/API projection update. It does not change the `agent_runtime` core protocol, provider loop, tool execution boundary, browser/HID boundary, or introduce migration scripts.

## Completed

- Added a normal Agent Management page entry from the desktop workspace sidebar.
- Added management page layout with left instance list, middle runtime conversation/tabs, and right runtime summary rail.
- Reframed Assistant and Autonomous as the same base agent surface with different trigger semantics:
  - Assistant: user message driven.
  - Autonomous: event/schedule/task driven.
- Removed goal-first wording from the management surface in favor of automation task/runtime terminology.
- Added timeline rendering for runtime conversation items:
  - `Thinking`
  - `Tool Call`
  - `Tool Result`
  - human instruction
  - human-in-the-loop confirmation
- Timeline mapping uses runtime item metadata such as `eventKind`, `itemType`, and `traceKind` instead of hardcoding legacy `message.kind` presentation behavior.
- Renamed the visible result label from `Execution Result` to `Tool Result`.
- Tool Result cards now size to actual content and do not repeat long task titles after the label.
- Timeline timestamps render as `HH:mm`, including old numeric second timestamps.
- Timeline nodes use event-specific icons instead of one generic green dot.
- Fixed auto-scroll behavior so polling the active autonomous conversation does not force the user back to the newest message while reading history.
- Reworked inline HITL confirmation into a compact decision card:
  - clean title
  - requester
  - business-facing reason
  - selectable decision strategy
  - optional note
  - approve/reject/all confirmations actions
- Internal runtime noise such as plan IDs, episode IDs, and long hash values is filtered out of inline confirmation cards.
- Approval strategy selection and notes are sent through the existing approval `reason` field.
- Backend agent workspace serialization now normalizes older timestamp shapes for UI reads.
- Backend autonomous conversation projection now includes run/turn level runtime output without duplicating the old goal row when real run messages exist.

## Files Changed

- `apps/desktop/src/components/Sidebar.tsx`
- `apps/desktop/src/features/workspace/DesktopWorkspace.tsx`
- `apps/desktop/src/features/chat-overlay/ChatOverlay.tsx`
- `apps/desktop/src/features/chat-overlay/ChatMessageStream.tsx`
- `apps/desktop/src/features/chat-overlay/ChatComposer.tsx`
- `apps/desktop/src/lib/api.ts`
- `apps/desktop/src/lib/types.ts`
- `apps/desktop/src/styles.css`
- `services/backend/src/recruit_agent/api/routers/agent.py`
- `services/backend/tests/api/test_agents_routes.py`

## Validation

Commands run:

```bash
npm --workspace apps/desktop run typecheck
PYTHONPATH=services/backend/src pytest -q services/backend/tests/api/test_agents_routes.py -q
```

Both passed.

Browser verification against `http://127.0.0.1:5174/`:

- Agent Management opens as a regular page.
- Timeline contains event-specific SVG nodes.
- `Execution Result` no longer appears.
- Tool Result cards render at natural content width.
- Confirmation timestamp renders as `HH:mm`.
- Inline confirmation card no longer exposes internal plan/episode/hash noise.
- Selecting a decision option updates UI state.
- Scrolling history remains stable across autonomous polling.

## Runtime State

During handoff:

- Frontend dev server was running on `127.0.0.1:5174`.
- Backend dev server was running on `127.0.0.1:8741`.

The Electron desktop dev command still depends on a healthy local Electron install; browser-based Vite verification was used for this pass.

## Non-Goals

- No database migration.
- No mock recruiting dataset committed.
- No browser-mcp or VirtualHID behavior change.
- No core `agent_runtime` protocol boundary change.
- No site-specific recruiting website logic added to runtime code.

## Remaining Optional Work

- Continue pixel tuning against the reference screenshots if stricter visual matching is required.
- Add Playwright screenshot regression coverage for the Agent Management page once the visual target stabilizes.
- Add richer backend event metadata for true provider-native `tool_call` / `tool_result` / `reasoning` items as more agent runtime traces are persisted.
