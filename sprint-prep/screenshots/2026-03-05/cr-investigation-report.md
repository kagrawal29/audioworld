# Investigation: 8 Disappeared Connection Requests (Mar 4)

**Date:** 2026-03-05
**Investigator:** LinkedIn Operator
**Mode:** Observation only, no actions taken

---

## Summary

8 connection requests sent on Mar 4 (Ad Agencies sprint) have disappeared. They are:
- NOT in the pending sent invitations list
- NOT connected (no acceptance)
- Profile buttons show "Connect" again (as if the CR was never sent)
- No withdrawal notices, no account warnings, no restrictions detected

## Affected Profiles

| # | Name | Profile URL | Current State | Degree |
|---|------|------------|---------------|--------|
| 1 | Jiggy Maru | /in/jiggy-maru-88b4a66a/ | Connect button visible | 2nd |
| 2 | Pritish Wesley | /in/pritishwesley/ | Connect button visible | 2nd |
| 3 | Swaty Pande | /in/swaty-pande-26b1a317/ | Connect button visible | (not visited) |
| 4 | Shraddha Ulhas Sane | /in/shraddha-ulhas-sane/ | Connect button visible | 2nd |
| 5 | Abhimanyu B. | /in/abhimanyu-balasubramanyam-b36706b5/ | Connect button visible | (not visited) |
| 6 | Nilan Ghosh | /in/nilan03/ | Connect button visible | 2nd |
| 7 | Sharang Pange | /in/sharangpange/ | Connect button visible | 2nd |
| 8 | Siddhartha Sanjay | /in/siddyartha/ | Connect button visible | 2nd |

All 8 were sent as plain Connect requests (no personalized note) during the Mar 4 sprint.

## What Was Checked

### 1. Sent Invitations Page (/mynetwork/invitation-manager/sent/)
- **Total pending: 24** (shown as "People (24)")
- Full list loaded and verified. None of the 8 names appear.
- All 24 pending invitations are from other sprints (Mar 3, Mar 4 personalized, and older)
- Screenshots: 01, 02, 03

### 2. Individual Profile Visits (6 of 8 checked)
- Jiggy Maru: "Connect" + "Message" buttons, 2nd degree (screenshot 04)
- Pritish Wesley: "Connect" + "Message" buttons, 2nd degree (screenshot 05)
- Shraddha Ulhas Sane: "Connect" + "Message" buttons, 2nd degree (screenshot 06)
- Nilan Ghosh: "Connect" + "Message" buttons, 2nd degree (screenshot 10)
- Sharang Pange: "Connect" + "Message" buttons, 2nd degree (screenshot 10)
- Siddhartha Sanjay: "Connect" + "Message" buttons, 2nd degree (screenshot 10)

### 3. Invitation Manager (Received tab)
- 6 received invitations pending (same as before: Girish, Anju, NDTV, Abhinav, Nishita, Aditya)
- No "withdrawn" section visible
- No mentions of declined or withdrawn invitations
- Screenshot: 07

### 4. Notifications Page
- Normal activity: post reactions, comments, profile views
- No warnings, restrictions, or violation notices
- No notifications about withdrawn or declined invitations
- GM Hakim engagement still visible (positive)
- Screenshots: 08, 09

### 5. Account Settings
- Clean settings page, no restriction banners
- No warning messages anywhere
- Connection count: 317 (unchanged from yesterday)
- Screenshot: 11

## Analysis: Why Did These CRs Disappear?

All 8 were plain Connect requests (no personalized note). The most likely explanations:

**1. LinkedIn auto-withdrew them (most likely)**
LinkedIn sometimes auto-withdraws connection requests that it flags as potentially automated or spam-like. This can happen when:
- Multiple plain CRs are sent in rapid succession
- The recipient profiles have high ignore/decline rates
- LinkedIn's internal spam detection triggers

**2. Recipients declined the requests**
When someone clicks "Ignore" on a connection request, the CR disappears from the sender's pending list and the Connect button reappears. LinkedIn does not notify the sender. This is the most benign explanation.

**3. LinkedIn's connection request quality filter**
Free accounts face stricter monitoring. Sending many plain (no note) CRs in one session can trigger LinkedIn's quality filter, which silently removes some requests.

## Key Observations

- The 9 CRs from Mar 4 that included personalized notes or were sent in earlier batches are still showing as pending (Alpa Jobalia with note, Sunny Jani with note, etc.)
- The disappeared CRs were ALL plain (no note) requests
- No account restrictions or warnings visible anywhere
- The Mar 3 sprint had 19 plain CRs, and 13 were accepted (62%). No similar disappearance.
- The timing suggests this happened overnight (between Mar 4 evening and Mar 5 morning)

## Recommendation

1. Do NOT resend these 8 CRs immediately. Wait 2-3 days to see if the pattern continues.
2. If resending, add personalized notes to the high-value targets (Pritish Wesley at Netflix, Shraddha Sane at The Mill).
3. For future sprints, consider spacing plain CRs more aggressively (3-5 min apart instead of 2-3 min).
4. Monitor the current 24 pending CRs over the next 24-48 hours for any further disappearances.
5. The account appears healthy otherwise. No restrictions, no warnings. This looks like silent CR removal rather than an account flag.
