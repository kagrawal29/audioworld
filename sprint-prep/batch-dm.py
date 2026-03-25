#!/usr/bin/env python3
"""Batch DM sender with robust flow."""

import requests
import json
import websocket
import time
import base64
import os
import sys
from urllib.parse import quote

SCREENSHOTS_DIR = '/root/Desktop/audioworld/sprint-prep/screenshots/2026-03-23'

def get_ws():
    tabs = requests.get('http://localhost:9222/json').json()
    for t in tabs:
        if 'linkedin.com' in t['url'] and 'protechts' not in t['url'] and 'merchantpool' not in t['url'] and 'ns1p.net' not in t['url']:
            return websocket.create_connection(t['webSocketDebuggerUrl']), t
    return websocket.create_connection(tabs[0]['webSocketDebuggerUrl']), tabs[0]

def send_cmd(ws, method, params=None, msg_id=1):
    cmd = {'id': msg_id, 'method': method}
    if params: cmd['params'] = params
    ws.send(json.dumps(cmd))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id: return resp

def evaluate(ws, expression, msg_id=1):
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expression, 'returnByValue': True, 'awaitPromise': True
    }, msg_id)
    return resp.get('result', {}).get('result', {}).get('value')

def screenshot(ws, fn):
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'}, 99)
    data = resp.get('result', {}).get('data', '')
    if data:
        with open(f'{SCREENSHOTS_DIR}/{fn}', 'wb') as f:
            f.write(base64.b64decode(data))
        return True
    return False


def send_dm_from_search(ws, search_query, dm_text, screenshot_name):
    """Search for 1st-degree connection, navigate to profile, send DM."""

    # Step 1: Search
    url = f'https://www.linkedin.com/search/results/people/?keywords={quote(search_query)}&network=%5B%22F%22%5D&origin=FACETED_SEARCH'
    send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(7)

    # Step 2: Get first result profile URL
    profile_url = evaluate(ws, '''
    (() => {
        var links = document.querySelectorAll('.entity-result__title-text a, a[href*="/in/"]');
        for (var l of links) {
            var href = l.href;
            if (href.includes('/in/') && !href.includes('/search/')) {
                return href;
            }
        }
        return 'not_found';
    })()
    ''')

    if profile_url == 'not_found':
        # Try without the connections filter
        url2 = f'https://www.linkedin.com/search/results/people/?keywords={quote(search_query)}&origin=GLOBAL_SEARCH_HEADER'
        send_cmd(ws, 'Page.navigate', {'url': url2})
        time.sleep(7)
        profile_url = evaluate(ws, '''
        (() => {
            var links = document.querySelectorAll('.entity-result__title-text a, a[href*="/in/"]');
            for (var l of links) {
                var href = l.href;
                if (href.includes('/in/') && !href.includes('/search/')) {
                    return href;
                }
            }
            return 'not_found';
        })()
        ''', 2)

    if profile_url == 'not_found':
        print(f"  NOT FOUND: {search_query}")
        return False

    print(f"  Profile: {profile_url[:60]}")

    # Step 3: Navigate to profile
    send_cmd(ws, 'Page.navigate', {'url': profile_url})
    time.sleep(7)

    name = evaluate(ws, 'document.querySelector("h1")?.innerText || ""', 3)
    print(f"  Name: {name}")

    # Step 4: Get Message href
    msg_href = evaluate(ws, '''
    (() => {
        var links = document.querySelectorAll('a');
        for (var l of links) {
            if (l.innerText.trim() === 'Message' && l.getBoundingClientRect().x < 600 && l.href.includes('messaging')) {
                return l.href;
            }
        }
        return 'not_found';
    })()
    ''', 4)

    if msg_href == 'not_found':
        print("  No Message link")
        screenshot(ws, screenshot_name)
        return False

    # Step 5: Navigate to compose
    send_cmd(ws, 'Page.navigate', {'url': msg_href})
    time.sleep(8)  # Longer wait for editor to load

    # Step 6: Type with retry
    escaped = dm_text.replace('`', '').replace('${', '')
    for attempt in range(3):
        type_result = evaluate(ws, f'''
        (() => {{
            var editor = document.querySelector('.msg-form__contenteditable') || document.querySelector('[contenteditable="true"]');
            if (!editor) return 'no_editor';
            editor.focus();
            document.execCommand('selectAll');
            document.execCommand('delete');
            document.execCommand('insertText', false, `{escaped}`);
            return 'typed:' + editor.innerText.substring(0, 80);
        }})()
        ''', 5 + attempt)

        if type_result and 'typed' in str(type_result):
            break
        time.sleep(2)

    print(f"  Type: {type_result}")
    if not type_result or 'no_editor' in str(type_result):
        screenshot(ws, screenshot_name)
        return False

    time.sleep(2)

    # Step 7: Send
    send_result = evaluate(ws, '''
    (() => {
        var btn = document.querySelector('.msg-form__send-button');
        if (btn && !btn.disabled) { btn.click(); return 'sent'; }
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.innerText.trim() === 'Send' && b.getBoundingClientRect().width > 30) {
                b.click();
                return 'sent';
            }
        }
        return 'not_found';
    })()
    ''', 10)
    print(f"  Send: {send_result}")

    time.sleep(3)
    screenshot(ws, screenshot_name)

    return 'sent' in str(send_result)


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'all'
    ws, tab = get_ws()

    dms = {
        'suuresh': {
            'search': 'Suuresh Ramachandran Eye-Q',
            'dm': "Hi Suuresh, been connected for a while but never got to introduce myself properly. I am Antara from The Audio World, a pan-India audio production house. We handle VO, dubbing, sound design, and audio post for films, ads, and corporate content. Eye-Q Films has been around for 21 years, that is impressive. If you ever need an audio production partner for any of your projects, would love to discuss.",
            'screenshot': '26-suuresh-dm.png'
        },
        'amitabha': {
            'search': 'Amitabha Singh Film Maker',
            'dm': "Hi Amitabha, thanks for connecting! I am Antara from The Audio World, a pan-India audio production house. We do voiceovers, dubbing, and audio post for films and content projects. What kind of films are you working on these days?",
            'screenshot': '27-amitabha-dm.png'
        },
        'sumit': {
            'search': 'Sumit Pande Podcast Producer',
            'dm': "Hi Sumit, thanks for connecting! I am Antara from The Audio World, we do audio production, VO, and sound design. Podcast production is a sweet spot for us. If you ever need voice talent, audio editing, or mixing for your podcasts, we can help. What shows are you working on?",
            'screenshot': '28-sumit-dm.png'
        },
        'munesh': {
            'search': 'Munesh Chaudhary Casting Director',
            'dm': "Hi Munesh, thanks for connecting! I am Antara from The Audio World, a pan-India VO and audio production house. We have a large roster of voice artists across Hindi and regional languages. If you ever handle VO casting or need voice talent for projects, we would love to be a resource. What kind of casting are you focused on?",
            'screenshot': '29-munesh-dm.png'
        },
        'kirubakaran': {
            'search': 'KIRUBAKARAN ALBERT',
            'dm': "Hi Kirubakaran, thanks for connecting! I am Antara from The Audio World, a pan-India audio production house. We handle VO, dubbing, and audio post for brands and agencies. If any of your brand strategy projects need audio or VO work, would love to collaborate. What kind of brands are you working with?",
            'screenshot': '30-kirubakaran-dm.png'
        }
    }

    if action in dms:
        spec = dms[action]
        print(f"Sending DM to {action}...")
        result = send_dm_from_search(ws, spec['search'], spec['dm'], spec['screenshot'])
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    elif action == 'all':
        for name, spec in dms.items():
            print(f"\n--- {name} ---")
            result = send_dm_from_search(ws, spec['search'], spec['dm'], spec['screenshot'])
            print(f"Result: {'SUCCESS' if result else 'FAILED'}")
            if name != list(dms.keys())[-1]:
                wait = 100 + (hash(name) % 30)
                print(f"Waiting {wait}s...")
                time.sleep(wait)

    ws.close()
