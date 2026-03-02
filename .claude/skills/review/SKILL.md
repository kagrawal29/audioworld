---
name: review
description: "Review a LinkedIn execution sheet before approval. Use when the user wants to review, check, or audit a prep sheet. Example: '/review' or '/review 2026-03-02'"
argument-hint: [date-optional]
---

## Review LinkedIn Execution Sheet

Review the execution sheet against quality standards before user approval.

### Steps

1. Find the most recent execution sheet in `sprint-prep/`. If a date argument was provided (`$ARGUMENTS`), use that specific file.

2. Read the full sheet.

3. Apply every check from the review checklist below:

4. Score each section:

**Connection Requests:**
- [ ] Every entry has: name, title, company, LinkedIn URL, connection degree
- [ ] Every note is personalized with specific work reference (not just company name)
- [ ] No `{placeholder}` text remains
- [ ] Count within 20/day limit
- [ ] Volume is ~2x daily plan target

**Comments:**
- [ ] ACTUAL posts identified with descriptions (not "find during sprint")
- [ ] Each comment references SPECIFIC post content
- [ ] Comments add value, not generic praise
- [ ] Post author and topic clearly noted

**DMs:**
- [ ] Personalized with prospect-specific context
- [ ] Within 25/day limit

**Profile Visits:**
- [ ] Strategic targets noted with reason for visit

**Execution Order:**
- [ ] Action types are mixed (not batched)
- [ ] Breaks scheduled every 5 actions
- [ ] Estimated sprint duration is reasonable (60-90 min)

5. Present a summary to the user:
   - **PASS** items (green)
   - **FAIL** items (need operator to redo)
   - **WARN** items (acceptable but could be better)

6. If any FAIL items: send operator back to fix specific gaps.
   If all PASS: tell user "Sheet is ready for your approval. Say `/sprint` to execute."
