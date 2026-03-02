---
name: prep
description: "Start Prep Mode for tomorrow's LinkedIn sprint. Use when the user wants to prepare outreach for a segment. Example: '/prep Ad Agencies' or '/prep Corporate Video'"
argument-hint: [segment-name]
---

## LinkedIn Sprint Prep Mode

You are activating **Prep Mode** for the LinkedIn operator.

**Target segment:** $ARGUMENTS

### Steps

1. Read the daily plan from the spreadsheet to confirm tomorrow's segment and targets:
   `/root/Desktop/audioworld/AudioWorld_March_2026_Touchpoints_with_Content_Library.xlsx`

2. Read the ICP details for the target segment from the `ICP_Segments` sheet to get:
   - Ideal Customer Profile
   - Decision makers to target
   - Pitch angle that wins
   - CTA to use

3. Read the relevant templates from the `Touchpoint_Library` sheet.

4. Calculate volume targets (2x the daily plan, within safe limits):
   - Connection requests: up to 20/day
   - Comments: up to 15/day
   - Profile visits: up to 30/day
   - DMs: up to 25/day

5. Send the operator (`linkedin-op`) into Prep Mode with a clear brief:
   - Segment + ICP details
   - Exact volume targets
   - Template base text for personalization
   - File path for the execution sheet: `sprint-prep/YYYY-MM-DD-segment.md`
   - Remind about pacing rules and actual-posts-only for comments

6. Tell the user: "Prep Mode activated for [segment]. The operator is building the execution sheet. I'll review it against the checklist when it's ready."

7. When the operator reports back, review using the checklist embedded in the review skill:
   `/root/Desktop/audioworld/.claude/skills/review/SKILL.md` (lines 22-45)

8. Present the sheet to the user for final approval. Flag any gaps.
