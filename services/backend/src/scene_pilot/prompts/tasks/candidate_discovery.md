# Task: Candidate Discovery

Discover candidate leads that fit the current recruiting goal and return a structured discovery result from the human operator's regular browser, not an AI-mode browser.

- Default recruiting source for this workflow: `zhipin.com`. If the human operator's regular browser does not currently have a reachable `zhipin.com` candidate-search, recommendation, or candidate-detail page open, ask the human to open `zhipin.com` to the relevant page before you continue.
- Do not depend on pre-labeled page entities. Infer candidate lists, profile panels, and resume clues from the raw browser snapshot, visible page text, and any DOM or page state you can inspect with the provided tools.
- When multiple recruiting tabs are open, inspect `zhipin.com` tabs first and prefer the one with the clearest candidate list, recommendation feed, or profile detail evidence.
- Start with `browser_snapshot` to understand the active scene. Use `browser_execute_script` when snapshot text is insufficient and you need more precise page structure or candidate field extraction.
- Prefer extraction over action. Do not send messages, do not request a resume, and do not mutate the recruiting site unless the goal explicitly requires a browser-side operation and that operation stays within the approved tool boundary.
- If you cannot isolate a credible candidate record from the current scene, return a structured failure or replan request instead of guessing. When the blocker is that `zhipin.com` is not open, say so explicitly and ask the human for that minimal action.
- When you succeed, include structured candidate facts, source evidence, and any visible resume or attachment signals you can verify from the current scene.
