#!/usr/bin/env python3
"""Job scout v3 — Navigate to each listing and extract full details."""

import sys
sys.path.insert(0, '/root/Desktop/audioworld/sprint-prep')
from cdp_helper import get_ws, navigate, evaluate, screenshot, scroll_down
import time
import json
import random

def random_delay(min_s=2, max_s=4):
    time.sleep(random.uniform(min_s, max_s))

def extract_job_details(ws, url):
    """Navigate to a job listing and extract full details using broad selectors."""
    navigate(ws, url, wait=6)

    # Use broad text-based extraction
    details = evaluate(ws, '''
        (() => {
            // Get the full page text from main content area
            const main = document.querySelector('main') || document.body;
            const fullText = main.innerText.substring(0, 3000);

            // Try to get structured data
            const h1 = document.querySelector('h1');
            const title = h1 ? h1.innerText.trim() : '';

            // Company — try multiple approaches
            let company = '';
            const companyLink = document.querySelector('a[href*="/company/"]');
            if (companyLink) company = companyLink.innerText.trim();

            // Poster / hiring manager
            let poster = '';
            const hiringEl = document.querySelector('[class*="hirer"], [class*="poster"]');
            if (hiringEl) poster = hiringEl.innerText.trim().substring(0, 200);

            // Also check for hiring manager link
            const hirerLink = document.querySelector('a[href*="/in/"]');
            let hirerProfile = '';
            if (hirerLink) {
                hirerProfile = hirerLink.href;
            }

            return JSON.stringify({
                title: title,
                company: company,
                poster: poster,
                hirer_profile: hirerProfile,
                full_text: fullText,
                url: window.location.href
            });
        })()
    ''')

    if details:
        try:
            return json.loads(details)
        except:
            return None
    return None

def main():
    ws = get_ws()

    # Deduplicated list of unique job URLs from the searches
    job_urls = [
        # "voice over artist" search results
        ('https://www.linkedin.com/jobs/view/4382690212/', 'Voice Over Artist (French) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4382671955/', 'Voice Over Artist (Hindi) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4381518572/', 'Voice Over Artist (Hindi)', 'Great Value Hiring'),
        ('https://www.linkedin.com/jobs/view/4382649977/', 'Voice Over Artist (American English) - Remote', 'Get Offers'),
        ('https://www.linkedin.com/jobs/view/4382399346/', 'Portuguese Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4382374935/', 'Turkish Voice Over Artist (Remote)', 'Nexus Consulting'),
        ('https://www.linkedin.com/jobs/view/4382379659/', 'Hindi Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4382379612/', 'Indonesian Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4382370644/', 'French Voice Over Artist (Remote)', 'Talent Bridge'),
        ('https://www.linkedin.com/jobs/view/4380381716/', 'Russian Voice Over Artist (Remote)', 'Talent Bridge'),
        # "voice actor" search results
        ('https://www.linkedin.com/jobs/view/4381329836/', 'Hindi Voice Actor | Remote', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381948033/', 'Voice Actor', 'Mercor'),
        ('https://www.linkedin.com/jobs/view/4381931470/', 'Voice Actor - Indian English', 'Alignerr'),
        ('https://www.linkedin.com/jobs/view/4323908496/', 'Voice Actor', 'DataAnnotation'),
        ('https://www.linkedin.com/jobs/view/4377110331/', 'Voice Actor - Freelance AI Trainer', 'Meridial Marketplace'),
        ('https://www.linkedin.com/jobs/view/4377095961/', 'Portuguese Voice Actor - AI Trainer', 'Meridial Marketplace'),
        ('https://www.linkedin.com/jobs/view/4377100623/', 'Welsh Voice Actor - AI Trainer', 'Meridial Marketplace'),
        # "narrator" search
        ('https://www.linkedin.com/jobs/view/4323905562/', 'Audiobook Narrator', 'DataAnnotation'),
        # "voice over artist" continued
        ('https://www.linkedin.com/jobs/view/4381342416/', 'Professional Voice Over Artist - Hindi', 'Crossing Hurdles'),
        ('https://www.linkedin.com/jobs/view/4381496605/', 'Voice Over Artist', 'MyRemoteTeam Inc'),
        # "video localization"
        ('https://www.linkedin.com/jobs/view/4289879197/', 'Telugu Video Localization Expert (Maths)', 'Khan Academy'),
        ('https://www.linkedin.com/jobs/view/4289873444/', 'Telugu Video Localization Expert (Science)', 'Khan Academy'),
        # "dubbing" search - Post Producer
        ('https://www.linkedin.com/jobs/view/4382919568/', 'Post Producer', 'Publicis Production'),
    ]

    results = []
    for i, (url, search_title, search_company) in enumerate(job_urls):
        print(f"\n--- [{i+1}/{len(job_urls)}] {search_title} ({search_company}) ---")
        random_delay(3, 6)

        details = extract_job_details(ws, url)
        if details:
            # Parse the full text to extract useful info
            text = details.get('full_text', '')

            # Extract location from text
            location = ''
            for line in text.split('\n'):
                line = line.strip()
                if 'India' in line and len(line) < 100:
                    location = line
                    break
                if '(Remote)' in line and len(line) < 100:
                    location = line
                    break

            # Check for posted date
            posted = ''
            for line in text.split('\n'):
                line = line.strip()
                if ('ago' in line.lower() or 'day' in line.lower()) and len(line) < 50:
                    posted = line
                    break

            result = {
                'title': details.get('title') or search_title,
                'company': details.get('company') or search_company,
                'location': location,
                'posted': posted,
                'poster': details.get('poster', ''),
                'hirer_profile': details.get('hirer_profile', ''),
                'url': url,
                'description_excerpt': text[:500] if text else ''
            }
            results.append(result)

            print(f"  Title: {result['title']}")
            print(f"  Company: {result['company']}")
            print(f"  Location: {result['location']}")
            print(f"  Poster: {result['poster'][:100] if result['poster'] else 'N/A'}")
            print(f"  Desc: {result['description_excerpt'][:200]}")
        else:
            results.append({
                'title': search_title,
                'company': search_company,
                'url': url,
                'description_excerpt': 'FAILED TO LOAD'
            })
            print(f"  FAILED to extract details")

    # Save and summarize
    with open('/tmp/job-scout-final.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*60}")
    print(f"FINAL SUMMARY: {len(results)} listings extracted")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r.get('title', 'N/A')}")
        print(f"   Company: {r.get('company', 'N/A')}")
        print(f"   Location: {r.get('location', 'N/A')}")
        print(f"   Posted: {r.get('posted', 'N/A')}")
        if r.get('poster'):
            print(f"   Poster: {r['poster'][:100]}")
        print(f"   URL: {r.get('url', 'N/A')}")

    print(f"\n\nSaved to /tmp/job-scout-final.json")

if __name__ == '__main__':
    main()
