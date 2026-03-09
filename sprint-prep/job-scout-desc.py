#!/usr/bin/env python3
"""Extract full job descriptions from key listings."""

import sys
sys.path.insert(0, '/root/Desktop/audioworld/sprint-prep')
from cdp_helper import get_ws, navigate, evaluate, scroll_down
import time
import json
import random

def random_delay(min_s=2, max_s=4):
    time.sleep(random.uniform(min_s, max_s))

def get_job_description(ws, url):
    """Navigate to job and extract full description."""
    navigate(ws, url, wait=5)
    time.sleep(1)

    # Scroll down to load description
    scroll_down(ws, 400)
    time.sleep(1)
    scroll_down(ws, 400)
    time.sleep(1)

    # Try clicking "Show more" if present
    evaluate(ws, '''
        (() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Show more') || b.innerText.includes('see more')) {
                    b.click();
                    return 'clicked show more';
                }
            }
            return 'no show more button';
        })()
    ''')
    time.sleep(1)

    # Extract description
    desc = evaluate(ws, '''
        (() => {
            // Try the jobs description container
            const descEl = document.querySelector('#job-details, .jobs-description__content, .jobs-description, [class*="jobs-description"]');
            if (descEl) return descEl.innerText.trim().substring(0, 1500);

            // Try article
            const article = document.querySelector('article');
            if (article) return article.innerText.trim().substring(0, 1500);

            // Fallback: get main content after the top card
            const main = document.querySelector('main');
            if (main) return main.innerText.trim().substring(0, 2000);

            return '';
        })()
    ''')

    # Also get the hiring person info
    poster = evaluate(ws, '''
        (() => {
            // Look for hirer card
            const hirerCard = document.querySelector('[class*="hirer-card"], [class*="hiring-team"]');
            if (hirerCard) return hirerCard.innerText.trim().substring(0, 200);

            // Look for "Meet the hiring team" section
            const sections = document.querySelectorAll('section, div');
            for (const s of sections) {
                const heading = s.querySelector('h2, h3');
                if (heading && (heading.innerText.includes('hiring team') || heading.innerText.includes('Posted by'))) {
                    return s.innerText.trim().substring(0, 300);
                }
            }
            return '';
        })()
    ''')

    return desc, poster

def main():
    ws = get_ws()

    # Key listings to get full descriptions for
    listings = [
        ('https://www.linkedin.com/jobs/view/4382690212/', 'Voice Over Artist (French) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4382671955/', 'Voice Over Artist (Hindi) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4381518572/', 'Voice Over Artist (Hindi)', 'Great Value Hiring'),
        ('https://www.linkedin.com/jobs/view/4382399346/', 'Portuguese Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4382379659/', 'Hindi Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4381329836/', 'Hindi Voice Actor | Remote', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381948033/', 'Voice Actor', 'Mercor'),
        ('https://www.linkedin.com/jobs/view/4381931470/', 'Voice Actor - Indian English', 'Alignerr'),
        ('https://www.linkedin.com/jobs/view/4323908496/', 'Voice Actor', 'DataAnnotation'),
        ('https://www.linkedin.com/jobs/view/4377110331/', 'Voice Actor - Freelance AI Trainer', 'Meridial Marketplace'),
        ('https://www.linkedin.com/jobs/view/4323905562/', 'Audiobook Narrator', 'DataAnnotation'),
        ('https://www.linkedin.com/jobs/view/4381342416/', 'Professional VO Artist - Hindi', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381496605/', 'Voice Over Artist', 'MyRemoteTeam Inc'),
        ('https://www.linkedin.com/jobs/view/4289879197/', 'Telugu Video Localization Expert (Maths)', 'Khan Academy'),
        ('https://www.linkedin.com/jobs/view/4382919568/', 'Post Producer', 'Publicis Production'),
    ]

    results = []
    for i, (url, title, company) in enumerate(listings):
        print(f"\n--- [{i+1}/{len(listings)}] {title} ({company}) ---")
        random_delay(3, 5)
        desc, poster = get_job_description(ws, url)
        print(f"  Description ({len(desc) if desc else 0} chars): {desc[:300] if desc else 'EMPTY'}")
        if poster:
            print(f"  Poster: {poster[:150]}")
        results.append({
            'url': url,
            'title': title,
            'company': company,
            'description': desc or '',
            'poster': poster or ''
        })

    with open('/tmp/job-scout-descriptions.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*60}")
    print("DESCRIPTIONS EXTRACTED")
    print(f"{'='*60}")
    for r in results:
        print(f"\n## {r['title']} ({r['company']})")
        print(f"URL: {r['url']}")
        if r['poster']:
            print(f"Poster: {r['poster'][:200]}")
        print(f"Description:\n{r['description'][:600]}")
        print("-" * 40)

if __name__ == '__main__':
    main()
