#!/usr/bin/env python3
"""Job scout — search LinkedIn Jobs for VO/dubbing/localization opportunities in India."""

import sys
sys.path.insert(0, '/root/Desktop/audioworld/sprint-prep')
from cdp_helper import get_ws, navigate, evaluate, screenshot, scroll_down
import time
import json
import random
import urllib.parse

def random_delay(min_s=3, max_s=6):
    """Human-like random delay."""
    time.sleep(random.uniform(min_s, max_s))

def search_jobs(ws, keyword):
    """Search LinkedIn Jobs for a keyword filtered to India."""
    # Build the LinkedIn Jobs search URL
    # geoId 102713980 = India
    encoded = urllib.parse.quote(keyword)
    url = f'https://www.linkedin.com/jobs/search/?keywords={encoded}&geoId=102713980&sortBy=DD'

    print(f"\n{'='*60}")
    print(f"Searching: '{keyword}' — India")
    print(f"URL: {url}")
    print(f"{'='*60}")

    navigate(ws, url, wait=6)

    # Check if logged in / page loaded
    page_info = evaluate(ws, 'JSON.stringify({title: document.title, url: window.location.href})')
    if page_info:
        info = json.loads(page_info)
        print(f"Page: {info.get('title', 'unknown')}")
        if 'login' in info.get('url', '').lower():
            print("ERROR: Not logged in!")
            return []

    # Wait for results to load
    time.sleep(3)

    # Get total result count
    total = evaluate(ws, '''
        (() => {
            const h = document.querySelector('.jobs-search-results-list__subtitle');
            return h ? h.innerText.trim() : 'unknown';
        })()
    ''')
    print(f"Results header: {total}")

    # Extract job listings
    results = evaluate(ws, '''
        (() => {
            const cards = document.querySelectorAll('.job-card-container, .jobs-search-results__list-item, li.jobs-search-results__list-item, .scaffold-layout__list-item');
            const jobs = [];
            for (let i = 0; i < Math.min(cards.length, 25); i++) {
                const card = cards[i];
                const titleEl = card.querySelector('.job-card-list__title, .job-card-container__link, a[data-control-name="job_card_title"]');
                const companyEl = card.querySelector('.job-card-container__primary-description, .job-card-container__company-name, .artdeco-entity-lockup__subtitle');
                const locationEl = card.querySelector('.job-card-container__metadata-item, .artdeco-entity-lockup__caption');
                const timeEl = card.querySelector('time, .job-card-container__listed-time');
                const linkEl = card.querySelector('a[href*="/jobs/view/"]');

                const title = titleEl ? titleEl.innerText.trim() : '';
                const company = companyEl ? companyEl.innerText.trim() : '';
                const location = locationEl ? locationEl.innerText.trim() : '';
                const posted = timeEl ? timeEl.innerText.trim() : '';
                const link = linkEl ? linkEl.href.split('?')[0] : '';

                if (title || company) {
                    jobs.push({ title, company, location, posted, link });
                }
            }
            return JSON.stringify(jobs);
        })()
    ''')

    if results:
        try:
            jobs = json.loads(results)
            print(f"Found {len(jobs)} job cards")
            for j in jobs:
                print(f"  - {j.get('title', 'N/A')} | {j.get('company', 'N/A')} | {j.get('location', 'N/A')} | {j.get('posted', 'N/A')}")
            return jobs
        except json.JSONDecodeError:
            print(f"Parse error: {results[:200]}")
            return []

    # If first selector didn't work, try alternative extraction
    print("Trying alternative selectors...")
    results2 = evaluate(ws, '''
        (() => {
            // Try a broader approach — get all job links
            const links = document.querySelectorAll('a[href*="/jobs/view/"]');
            const seen = new Set();
            const jobs = [];
            for (const a of links) {
                const href = a.href.split('?')[0];
                if (seen.has(href)) continue;
                seen.add(href);

                // Walk up to find the card container
                let card = a.closest('li') || a.closest('[data-occludable-job-id]') || a.parentElement;
                const title = a.innerText.trim() || '';

                // Find company and location near this link
                let company = '';
                let location = '';
                let posted = '';
                if (card) {
                    const texts = card.innerText.split('\\n').map(t => t.trim()).filter(t => t);
                    // Usually: title, company, location, posted
                    if (texts.length >= 2) company = texts[1] || '';
                    if (texts.length >= 3) location = texts[2] || '';
                    if (texts.length >= 4) posted = texts[texts.length - 1] || '';
                }

                if (title) {
                    jobs.push({ title: title.substring(0, 100), company: company.substring(0, 100), location: location.substring(0, 100), posted: posted.substring(0, 50), link: href });
                }
            }
            return JSON.stringify(jobs.slice(0, 25));
        })()
    ''')

    if results2:
        try:
            jobs = json.loads(results2)
            print(f"Found {len(jobs)} job cards (alt selector)")
            for j in jobs:
                print(f"  - {j.get('title', 'N/A')} | {j.get('company', 'N/A')} | {j.get('location', 'N/A')}")
            return jobs
        except json.JSONDecodeError:
            print(f"Alt parse error: {results2[:200]}")

    # Last resort: take screenshot to see what's on page
    print("No results from selectors. Taking screenshot...")
    screenshot(ws, '/tmp/job-scout-debug.png')

    # Try getting raw page text
    raw = evaluate(ws, 'document.querySelector("main")?.innerText?.substring(0, 2000) || "no main element"')
    print(f"Page text excerpt: {raw[:500] if raw else 'empty'}")

    return []

def scroll_and_load_more(ws):
    """Scroll down to load more job listings."""
    for _ in range(3):
        scroll_down(ws, 500)
        time.sleep(1)

def main():
    ws = get_ws()

    # Verify we're logged in
    navigate(ws, 'https://www.linkedin.com/feed/', wait=5)
    page_info = evaluate(ws, 'JSON.stringify({title: document.title, url: window.location.href})')
    if page_info:
        info = json.loads(page_info)
        print(f"LinkedIn status: {info.get('title', 'unknown')}")
        if 'login' in info.get('url', '').lower():
            print("ERROR: Not logged in to LinkedIn!")
            sys.exit(1)

    all_results = {}

    keywords = [
        "voiceover",
        "dubbing",
        "voice actor",
        "localization",
        "audio production"
    ]

    for kw in keywords:
        random_delay(5, 10)  # Wait between searches
        jobs = search_jobs(ws, kw)
        scroll_and_load_more(ws)

        # Try to get more after scrolling
        more = evaluate(ws, '''
            (() => {
                const links = document.querySelectorAll('a[href*="/jobs/view/"]');
                const seen = new Set();
                const jobs = [];
                for (const a of links) {
                    const href = a.href.split('?')[0];
                    if (seen.has(href)) continue;
                    seen.add(href);
                    let card = a.closest('li') || a.parentElement;
                    const title = a.innerText.trim() || '';
                    let company = '';
                    let location = '';
                    let posted = '';
                    if (card) {
                        const texts = card.innerText.split('\\n').map(t => t.trim()).filter(t => t);
                        if (texts.length >= 2) company = texts[1] || '';
                        if (texts.length >= 3) location = texts[2] || '';
                    }
                    if (title) {
                        jobs.push({ title: title.substring(0, 100), company: company.substring(0, 100), location: location.substring(0, 100), posted, link: href });
                    }
                }
                return JSON.stringify(jobs.slice(0, 25));
            })()
        ''')

        if more:
            try:
                more_jobs = json.loads(more)
                # Merge — keep unique by link
                existing_links = {j.get('link') for j in jobs}
                for j in more_jobs:
                    if j.get('link') and j['link'] not in existing_links:
                        jobs.append(j)
                        existing_links.add(j['link'])
            except:
                pass

        all_results[kw] = jobs
        print(f"\nTotal for '{kw}': {len(jobs)} listings")

    # Summary
    print(f"\n\n{'='*60}")
    print("JOB SCOUT SUMMARY")
    print(f"{'='*60}")
    total = 0
    for kw, jobs in all_results.items():
        print(f"\n[{kw}] — {len(jobs)} listings")
        for j in jobs:
            print(f"  Title: {j.get('title', 'N/A')}")
            print(f"  Company: {j.get('company', 'N/A')}")
            print(f"  Location: {j.get('location', 'N/A')}")
            print(f"  Posted: {j.get('posted', 'N/A')}")
            print(f"  Link: {j.get('link', 'N/A')}")
            print()
        total += len(jobs)

    print(f"\nTotal listings across all searches: {total}")

    # Save results to JSON for further processing
    with open('/tmp/job-scout-results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print("\nResults saved to /tmp/job-scout-results.json")

if __name__ == '__main__':
    main()
