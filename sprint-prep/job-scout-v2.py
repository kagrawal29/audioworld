#!/usr/bin/env python3
"""Job scout v2 — click into listings to check job descriptions for relevance."""

import sys
sys.path.insert(0, '/root/Desktop/audioworld/sprint-prep')
from cdp_helper import get_ws, navigate, evaluate, screenshot, scroll_down
import time
import json
import random
import urllib.parse

def random_delay(min_s=3, max_s=6):
    time.sleep(random.uniform(min_s, max_s))

def search_and_extract(ws, keyword, extra_params=""):
    """Search LinkedIn Jobs and extract listings with job descriptions."""
    encoded = urllib.parse.quote(keyword)
    url = f'https://www.linkedin.com/jobs/search/?keywords={encoded}&geoId=102713980&sortBy=DD{extra_params}'

    print(f"\n{'='*60}")
    print(f"Searching: '{keyword}' — India")
    print(f"{'='*60}")

    navigate(ws, url, wait=7)

    # Get the result count text
    count_text = evaluate(ws, '''
        (() => {
            // Try multiple selectors for result count
            const selectors = [
                '.jobs-search-results-list__subtitle',
                '.jobs-search-results-list__title-heading',
                '.jobs-search-results-list__text',
                'h2.jobs-search-results-list__title'
            ];
            for (const s of selectors) {
                const el = document.querySelector(s);
                if (el && el.innerText.trim()) return el.innerText.trim();
            }
            // Try header area text
            const header = document.querySelector('.jobs-search-results-list');
            if (header) {
                const h = header.querySelector('h1, h2, h3');
                if (h) return h.innerText.trim();
            }
            return 'count not found';
        })()
    ''')
    print(f"Count: {count_text}")

    # Get list item texts to see what's actually showing
    items_text = evaluate(ws, '''
        (() => {
            // Get the job list container
            const list = document.querySelector('.jobs-search-results-list, .scaffold-layout__list');
            if (!list) return 'no list found';

            // Get all list items
            const items = list.querySelectorAll('li');
            const results = [];
            for (let i = 0; i < Math.min(items.length, 25); i++) {
                const text = items[i].innerText.trim().replace(/\\n+/g, ' | ').substring(0, 200);
                if (text.length > 20) results.push(text);
            }
            return JSON.stringify(results);
        })()
    ''')

    if items_text:
        try:
            items = json.loads(items_text)
            print(f"\nList items ({len(items)}):")
            for i, item in enumerate(items):
                print(f"  {i+1}. {item}")
        except:
            print(f"Raw: {items_text[:500]}")

    # Also get all job links
    links = evaluate(ws, '''
        (() => {
            const anchors = document.querySelectorAll('a[href*="/jobs/view/"]');
            const seen = new Set();
            const results = [];
            for (const a of anchors) {
                const href = a.href.split('?')[0];
                if (seen.has(href)) continue;
                seen.add(href);
                results.push({
                    text: a.innerText.trim().substring(0, 100),
                    href: href
                });
            }
            return JSON.stringify(results);
        })()
    ''')

    if links:
        try:
            link_list = json.loads(links)
            print(f"\nJob links ({len(link_list)}):")
            for l in link_list:
                print(f"  {l['text']} -> {l['href']}")
        except:
            print(f"Links raw: {links[:500]}")

    return items_text, links

def click_job_and_read(ws, job_url):
    """Navigate to a job listing and extract details."""
    navigate(ws, job_url, wait=5)

    details = evaluate(ws, '''
        (() => {
            const title = document.querySelector('.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1')?.innerText?.trim() || '';
            const company = document.querySelector('.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name')?.innerText?.trim() || '';
            const location = document.querySelector('.job-details-jobs-unified-top-card__workplace-type, .jobs-unified-top-card__workplace-type')?.innerText?.trim() || '';
            const posted = document.querySelector('.job-details-jobs-unified-top-card__posted-date, .jobs-unified-top-card__posted-date')?.innerText?.trim() || '';

            // Get job description
            const descEl = document.querySelector('.jobs-description__content, .jobs-description, #job-details');
            const description = descEl ? descEl.innerText.trim().substring(0, 1000) : '';

            // Get poster info
            const posterEl = document.querySelector('.jobs-poster__name, .hirer-card__hirer-information');
            const poster = posterEl ? posterEl.innerText.trim().substring(0, 200) : '';

            // Broader extraction
            const topCard = document.querySelector('.job-details-jobs-unified-top-card__container, .jobs-unified-top-card');
            const topText = topCard ? topCard.innerText.trim().substring(0, 500) : '';

            return JSON.stringify({ title, company, location, posted, description, poster, topText });
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

    all_relevant = []

    # Strategy: Use more specific search terms and also try clicking into results
    searches = [
        # Core VO/dubbing searches
        ('"voice over artist"', ''),
        ('"voiceover artist"', ''),
        ('"dubbing artist"', ''),
        ('"voice actor"', ''),
        ('"narrator"', ''),
        # Company-demand signals
        ('"voice over" production', ''),
        ('"dubbing" studio', ''),
        ('"audio localization"', ''),
        ('"video localization"', ''),
    ]

    for keyword, extra in searches:
        random_delay(5, 10)
        items_text, links_text = search_and_extract(ws, keyword, extra)

        # Parse links and check for VO-relevant job titles
        if links_text:
            try:
                link_list = json.loads(links_text)
                for link in link_list:
                    title_lower = link['text'].lower()
                    # Check if job title contains relevant keywords
                    relevant_words = ['voice', 'vo ', 'narrator', 'dubbing', 'dub ', 'localization',
                                     'audio', 'sound', 'recording', 'podcast', 'media', 'content creator',
                                     'video editor', 'post production', 'post-production']
                    if any(w in title_lower for w in relevant_words):
                        print(f"\n  ** RELEVANT: {link['text']} -> {link['href']}")

                        # Click into the listing to get full details
                        random_delay(2, 4)
                        details = click_job_and_read(ws, link['href'])
                        if details:
                            details['search_keyword'] = keyword
                            details['job_url'] = link['href']
                            all_relevant.append(details)
                            print(f"     Company: {details.get('company', 'N/A')}")
                            print(f"     Top: {details.get('topText', 'N/A')[:200]}")
                            desc_preview = details.get('description', '')[:200]
                            print(f"     Desc: {desc_preview}")

                        # Navigate back to search results
                        random_delay(2, 3)
            except json.JSONDecodeError:
                pass

    # Also check the earlier "voice actor" results which had real listings
    print("\n\n--- Checking known relevant listings from first scan ---")
    known_relevant = [
        'https://www.linkedin.com/jobs/view/4382690212/',  # VO Artist (French)
        'https://www.linkedin.com/jobs/view/4381518572/',  # VO Artist (Hindi)
        'https://www.linkedin.com/jobs/view/4382399346/',  # Portuguese VO Artist
        'https://www.linkedin.com/jobs/view/4382374935/',  # Turkish VO Artist
        'https://www.linkedin.com/jobs/view/4381342416/',  # Professional VO Artist Hindi
        'https://www.linkedin.com/jobs/view/4381496605/',  # VO Artist (MyRemoteTeam)
        'https://www.linkedin.com/jobs/view/4381948033/',  # Voice Actor (Mercor)
        'https://www.linkedin.com/jobs/view/4382919568/',  # Post Producer (Publicis)
    ]

    seen_urls = {r.get('job_url') for r in all_relevant}
    for url in known_relevant:
        if url in seen_urls:
            print(f"  Already have: {url}")
            continue
        random_delay(3, 5)
        details = click_job_and_read(ws, url)
        if details:
            details['job_url'] = url
            details['search_keyword'] = 'initial scan'
            all_relevant.append(details)
            print(f"\n  Title: {details.get('title', 'N/A')}")
            print(f"  Company: {details.get('company', 'N/A')}")
            print(f"  Top: {details.get('topText', 'N/A')[:200]}")
            desc_preview = details.get('description', '')[:200]
            print(f"  Desc: {desc_preview}")

    # Final summary
    print(f"\n\n{'='*60}")
    print(f"FINAL RESULTS: {len(all_relevant)} relevant listings")
    print(f"{'='*60}")
    for i, r in enumerate(all_relevant, 1):
        print(f"\n--- Listing {i} ---")
        print(f"Title: {r.get('title', 'N/A')}")
        print(f"Company: {r.get('company', 'N/A')}")
        print(f"Location: {r.get('location', 'N/A')}")
        print(f"Posted: {r.get('posted', 'N/A')}")
        print(f"Poster: {r.get('poster', 'N/A')}")
        print(f"URL: {r.get('job_url', 'N/A')}")
        print(f"Search: {r.get('search_keyword', 'N/A')}")
        print(f"Description: {r.get('description', 'N/A')[:300]}")

    # Save
    with open('/tmp/job-scout-v2-results.json', 'w') as f:
        json.dump(all_relevant, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to /tmp/job-scout-v2-results.json")

if __name__ == '__main__':
    main()
