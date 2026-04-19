# Task: Job Description Sync

Synchronize job descriptions from the recruiting platform pages currently reachable in the human operator's regular browser, not an AI-mode browser, into the local shared workspace job-description store.

- Default recruiting source for this workflow: `zhipin.com`. If the human operator's regular browser does not currently have a reachable `zhipin.com` recruiting page open, ask the human to open `zhipin.com` to a relevant job list or job detail page before you continue.
- Source of truth for this task: the recruiting pages you can currently inspect from the human operator's regular browser through generic browser tools across all open tabs that are reachable without human intervention.
- Destination of this task: the local shared workspace job-description store, which you read with `list_job_descriptions` and write with `upsert_job_description`.
- Interpret `constraints.sync_mode` literally.
  - `initial`: perform a first-pass import for the visible and reachable recruiting scope. Capture every confirmed role you can reach in that scope and write it into the workspace.
  - `incremental`: compare the roles you currently observe on the recruiting surface against the existing local workspace roles. Create missing local records, update records whose externally observable fields changed, and skip unchanged records.
- For incremental sync, do not delete, archive, or close a local role only because it is absent from the currently visible remote scope unless the task explicitly asks for that mutation.
- Use only generic recruiting reasoning. Do not assume any site-specific selectors, page labels, or pre-wired platform adapters.
- Treat the regular browser state as something you must inspect and classify yourself. Do not assume the active tab is the correct tab, and do not ask the operator to switch tabs until you have exhausted the tabs that are already open.
- Start by enumerating the currently open browser tabs, then classify each tab from visible evidence such as title, URL, and structured snapshot text into one of: likely job-description scene, likely unrelated scene, or uncertain scene.
- For every tab that is likely job-description related or uncertain, inspect it further before you declare the sync blocked. Prefer `zhipin.com` tabs first, then prefer the tab with the strongest evidence of a recruiting surface, such as visible role cards, job lists, role detail panels, or recruiting workflow text.
- Only return `blocked` when you have already checked the currently reachable tabs and still cannot find a usable `zhipin.com` recruiting scene, or when the remaining path clearly requires human help such as login, captcha, permissions, or a missing `zhipin.com` recruiting page.
- Persist every confirmed role through `upsert_job_description`. Include stable external identity when you can observe one, such as a platform id, job id in the URL, or another durable site identifier.
- Before writing, check existing local roles with `list_job_descriptions` whenever you need to match remote roles to existing workspace records, avoid duplicate work, or estimate sync progress.
- Treat `title` as required. Capture other fields only when they are visible or directly derivable from evidence on the page. Do not guess salary, location, department, or requirements.
- If the page requires navigation to reveal more roles, use the available generic browser tools to continue the sync loop. Stop only when the visible scope is exhausted, blocked, or requires human help.
- If you decide the task is blocked, explain which tabs or browser scenes you inspected, why each one was rejected, and what minimal human action would unblock you, such as opening `zhipin.com` to the correct recruiting page. Do not pretend the sync is complete when you only verified that the current page is unrelated.
- Do not perform outbound communication or other high-risk mutations on the external recruiting site during this task.
- Finish with a concise structured summary of how many roles were created, updated, skipped, or blocked, and cite the observed evidence for anything uncertain.
