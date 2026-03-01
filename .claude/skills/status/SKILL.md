---
name: status
description: "Check the current status of the LinkedIn operator, active sprint, or daily progress. Use when user asks 'what's happening', 'status', 'where are we', 'how's it going'."
---

## LinkedIn Operator Status Check

### Steps

1. Check the team state — is the operator (`linkedin-op`) spawned and active?

2. Check for any in-progress execution sheet in `sprint-prep/` — read its status field.

3. Read operator memory at `~/.claude/agent-memory/linkedin-operator/` for today's action log.

4. Read the spreadsheet's daily plan row for today to compare planned vs actual.

5. Present a compact status to the user:

```
## Status — [Today's Date]
**Operator:** [active / idle / not spawned]
**Mode:** [Prep / Sprint / Standby]
**Today's Segment:** [from spreadsheet]

### Progress
| Action | Planned | Prepped | Approved | Executed |
|--------|---------|---------|----------|----------|
| Connections | X | X | X | X |
| DMs | X | X | X | X |
| Comments | X | X | X | X |
| Profile Visits | X | X | X | X |
| **Total** | X | X | X | X |

**Next step:** [what needs to happen next]
```

6. If there are blocked items or issues, flag them clearly.
