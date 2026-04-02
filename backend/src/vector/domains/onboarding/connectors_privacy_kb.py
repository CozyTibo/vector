"""Ground-truth copy for onboarding Q&A: integrations, signals, not sensitive bulk data.

Product/legal should review periodically. Injected into the LLM system prompt only during
`profile_phase == connectors_intro`.
"""

from __future__ import annotations

# Keep factual and aligned with product positioning; avoid overpromising legal guarantees.
CONNECTORS_PRIVACY_KNOWLEDGE_BASE = """
### Principles (all tools)
- Vector connects to the tools you authorize so we can surface **execution signals**: who did what,
  when work moved, and lightweight metadata that helps you run the team. We are not building a
  full archive of your private content.
- **We do not use your connected data to train public ML models.**
- OAuth / app installs are scoped to what each provider exposes for that integration; you can
  revoke access from the provider or from Vector settings.

### Slack
- **Purpose:** Slack is how Vector **talks with you** in your workspace (mentions, DMs, slash-style
  flows as you ship them). It is the interaction surface, not a datastore of your full history.
- **Data posture:** We do **not** store your Slack message bodies or a searchable copy of
  conversations for onboarding or analytics in the way a backup or e-discovery product would.
  We use what is needed to deliver the in-Slack experience and the **signals** we show in Vector
  (e.g. that something was requested or answered in channel when relevant to execution).
- **Reassurance line you can paraphrase:** "Slack is for working with Vector in your workspace;
  we are not warehousing your chats."

### GitHub
- **Purpose:** We connect to understand **engineering activity**: PRs, issues, reviews, merges,
  and related metadata that reflects how work flows.
- **Data posture:** We **do not pull or retain your source code contents** for browsing or storage
  in the product sense described in onboarding. We work from **activity and metadata** (titles,
  states, timelines, reviewers, etc.), not from reading or copying repository file contents.
- If asked about security reviews: scopes are minimal for the integration; secret scanning and
  branch protection remain on GitHub's side.

### Linear (and similar PM tools)
- **Purpose:** Issue and project **signals**: status, assignee, cycle, priority, timeline of
  changes, not a full export of every comment thread for unrelated purposes.
- **Data posture:** Metadata and state changes that describe work in motion; avoid implying we
  ingest full specs or confidential attachments unless product explicitly does later.

### Docs (Notion, Confluence, Google Docs, etc.)
- **Purpose:** When connected, typically **titles, links, and light structure** so Vector knows
  what docs exist around work, not to mirror full document bodies unless product scope changes.
- If the user picks a tool we have not wired yet: say we only OAuth the tools in the upcoming
  picker flow and they can ask support for detail.

### If they ask "do you store everything?"
- Short honest answer: **No.** We focus on **signals** needed for execution visibility and for
  Vector to operate (Slack interaction, activity from GitHub/Linear, etc.), not on hoarding
  sensitive content like full code or full chat logs.

### If they ask legal / DPA / subprocessors
- Say you cannot provide legal advice; point them to published privacy policy / security page
  or their Vector contact for enterprise terms.
"""
