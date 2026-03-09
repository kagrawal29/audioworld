#!/usr/bin/env python3
"""Get full job descriptions and hiring manager details for the most relevant listings."""

import sys
sys.path.insert(0, '/root/Desktop/audioworld/sprint-prep')
from cdp_helper import get_ws, navigate, evaluate, scroll_down
import time
import json
import random

def random_delay(min_s=2, max_s=4):
    time.sleep(random.uniform(min_s, max_s))

def get_full_details(ws, url):
    """Get full job description and hiring manager details."""
    navigate(ws, url, wait=5)
    time.sleep(1)

    # Click "Show more" / "...see more" in description if present
    evaluate(ws, '''
        (() => {
            const btns = document.querySelectorAll('button, a');
            for (const b of btns) {
                const text = b.innerText.trim().toLowerCase();
                if (text === 'show more' || text === '…see more' || text === 'see more') {
                    b.click();
                    return 'clicked';
                }
            }
            return 'no button';
        })()
    ''')
    time.sleep(1)

    # Scroll to load full content
    scroll_down(ws, 500)
    time.sleep(1)
    scroll_down(ws, 500)
    time.sleep(1)

    # Extract everything
    result = evaluate(ws, '''
        (() => {
            const main = document.querySelector('main') || document.body;
            const fullText = main.innerText;

            // Find "About the job" section
            const aboutIdx = fullText.indexOf('About the job');
            let description = '';
            if (aboutIdx !== -1) {
                description = fullText.substring(aboutIdx + 14, aboutIdx + 2000).trim();
            }

            // Find hiring team info
            let hirer = '';
            const hirerIdx = fullText.indexOf('Meet the hiring team');
            if (hirerIdx !== -1) {
                hirer = fullText.substring(hirerIdx, hirerIdx + 300).trim();
            }

            // Find company link
            const companyLink = document.querySelector('a[href*="/company/"]');
            const companyUrl = companyLink ? companyLink.href.split('?')[0] : '';
            const companyName = companyLink ? companyLink.innerText.trim() : '';

            // Find poster profile link
            let posterUrl = '';
            const posterLinks = document.querySelectorAll('a[href*="/in/"]');
            for (const a of posterLinks) {
                const parent = a.closest('[class*="hirer"], [class*="hiring"]');
                if (parent || a.closest('section')?.innerText?.includes('hiring team')) {
                    posterUrl = a.href.split('?')[0];
                    break;
                }
            }

            return JSON.stringify({
                description: description.substring(0, 1500),
                hirer: hirer,
                companyUrl: companyUrl,
                companyName: companyName,
                posterUrl: posterUrl
            });
        })()
    ''')

    if result:
        try:
            return json.loads(result)
        except:
            pass
    return {}

def main():
    ws = get_ws()

    # Focus on the most outreach-relevant listings
    # Skip AI training roles (DataAnnotation, Mercor, Alignerr, Meridial) — they're looking for individual VO artists, not a studio
    # Focus on: production companies, agencies, platforms that might hire studios

    priority_listings = [
        # Companies that might need a VO studio
        ('https://www.linkedin.com/jobs/view/4382690212/', 'VO Artist (French) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4382671955/', 'VO Artist (Hindi) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4381518572/', 'VO Artist (Hindi)', 'Great Value Hiring'),
        ('https://www.linkedin.com/jobs/view/4382399346/', 'Portuguese VO Artist', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4382379659/', 'Hindi VO Artist', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4381329836/', 'Hindi Voice Actor', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381342416/', 'Professional VO Artist Hindi', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381496605/', 'Voice Over Artist', 'MyRemoteTeam Inc'),
        ('https://www.linkedin.com/jobs/view/4289879197/', 'Telugu Video Localization (Maths)', 'Khan Academy'),
        ('https://www.linkedin.com/jobs/view/4289873444/', 'Telugu Video Localization (Science)', 'Khan Academy'),
        ('https://www.linkedin.com/jobs/view/4382919568/', 'Post Producer', 'Publicis Production'),
    ]

    results = []
    for i, (url, title, company) in enumerate(priority_listings):
        print(f"\n--- [{i+1}/{len(priority_listings)}] {title} ({company}) ---")
        random_delay(3, 5)
        details = get_full_details(ws, url)
        details['url'] = url
        details['title'] = title
        details['company_search'] = company
        results.append(details)

        print(f"  Company: {details.get('companyName', 'N/A')} ({details.get('companyUrl', '')})")
        print(f"  Hirer: {details.get('hirer', 'N/A')[:150]}")
        print(f"  Poster URL: {details.get('posterUrl', 'N/A')}")
        print(f"  Description: {details.get('description', 'N/A')[:300]}")

    with open('/tmp/job-scout-details.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\nSaved to /tmp/job-scout-details.json")

if __name__ == '__main__':
    main()
