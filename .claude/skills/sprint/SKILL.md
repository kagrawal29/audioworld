---
name: sprint
description: "Start Sprint Mode to execute an approved LinkedIn execution sheet. Use when the user approves a prep sheet and says 'go', 'approved', 'start sprint', 'execute'. Example: '/sprint' or '/sprint 2026-03-02'"
argument-hint: [date-optional]
---

## LinkedIn Sprint Mode — Execute Approved Sheet

The user has approved the execution sheet. Time to execute.

### Steps

1. Find the most recent execution sheet in `sprint-prep/`. If a date argument was provided (`$ARGUMENTS`), use that specific file.

2. Verify the sheet is marked as approved. If not, ask the user to confirm approval first.

3. Mark the sheet status as "APPROVED — SPRINT IN PROGRESS".

4. Send the operator (`linkedin-op`) into Sprint Mode with:
   - The exact file path of the approved sheet
   - Reminder: execute line by line, in the specified order
   - Reminder: human pacing is non-negotiable (from field manual)
   - Reminder: report progress every 3-4 actions
   - Reminder: CAPTCHA or any warning = full stop

5. Monitor operator progress reports. For each report:
   - Acknowledge to the user with a brief status update
   - Flag any failures or skipped actions
   - Track total completed vs remaining

6. When sprint is complete:
   - Ask operator for final summary (actions completed, failed, skipped)
   - Update the spreadsheet's "Actual" columns if possible
   - Log the sprint results to operator memory
   - Present final report to user
