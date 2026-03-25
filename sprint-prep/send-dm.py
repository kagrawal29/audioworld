#!/usr/bin/env python3
"""Send DM to a person by navigating to their profile first."""

import requests
import json
import websocket
import time
import base64
import os
import sys
from urllib.parse import quote

SCREENSHOTS_DIR = '/root/Desktop/audioworld/sprint-prep/screenshots/2026-03-23'
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

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

def screenshot(ws, filename):
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'}, 99)
    data = resp.get('result', {}).get('data', '')
    if data:
        path = os.path.join(SCREENSHOTS_DIR, filename)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data))
        return True
    return False


def send_dm_via_profile_search(ws, search_query, dm_text, screenshot_name):
    """Search for person, navigate to profile, get Message href, send DM."""

    # Step 1: Search LinkedIn people
    url = f'https://www.linkedin.com/search/results/people/?keywords={quote(search_query)}&network=%5B%22F%22%5D&origin=FACETED_SEARCH'
    send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(7)

    # Find profile URL
    profile_url = evaluate(ws, '''
    (() => {
        var links = document.querySelectorAll('.entity-result__title-text a');
        for (var a of links) {
            return a.href;
        }
        return 'not_found';
    })()
    ''')

    if profile_url == 'not_found':
        print(f"  Person not found in search: {search_query}")
        return False

    print(f"  Profile: {profile_url[:80]}")

    # Step 2: Navigate to profile
    send_cmd(ws, 'Page.navigate', {'url': profile_url})
    time.sleep(6)

    # Step 3: Get Message href
    msg_href = evaluate(ws, '''
    (() => {
        var links = document.querySelectorAll('a');
        for (var l of links) {
            if (l.innerText.trim() === 'Message' && l.getBoundingClientRect().x < 600) {
                return l.href;
            }
        }
        return 'not_found';
    })()
    ''', 2)

    if msg_href == 'not_found':
        print("  Message link not found on profile")
        screenshot(ws, screenshot_name)
        return False

    print(f"  Message href found")

    # Step 4: Navigate to messaging compose
    send_cmd(ws, 'Page.navigate', {'url': msg_href})
    time.sleep(6)

    # Step 5: Type message
    escaped = dm_text.replace('\\', '\\\\').replace("'", "\\'")
    type_result = evaluate(ws, f'''
    (() => {{
        var editor = document.querySelector('.msg-form__contenteditable') ||
                     document.querySelector('[contenteditable="true"][aria-label*="Write a message"]');
        if (!editor) return 'editor_not_found';
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('delete');
        document.execCommand('insertText', false, '{escaped}');
        return 'typed:' + editor.innerText.substring(0, 80);
    }})()
    ''', 3)
    print(f"  Type: {type_result}")

    if not type_result or 'not_found' in str(type_result):
        screenshot(ws, screenshot_name)
        return False

    time.sleep(2)

    # Step 6: Send
    send_result = evaluate(ws, '''
    (() => {
        var btn = document.querySelector('.msg-form__send-button');
        if (btn) { btn.click(); return 'sent'; }
        return 'send_not_found';
    })()
    ''', 4)
    print(f"  Send: {send_result}")

    time.sleep(3)
    screenshot(ws, screenshot_name)

    return 'sent' in str(send_result)


def send_dm_via_profile_url(ws, profile_url, dm_text, screenshot_name):
    """Send DM given an exact profile URL."""

    # Navigate to profile
    send_cmd(ws, 'Page.navigate', {'url': profile_url})
    time.sleep(6)

    # Get Message href
    msg_href = evaluate(ws, '''
    (() => {
        var links = document.querySelectorAll('a');
        for (var l of links) {
            if (l.innerText.trim() === 'Message' && l.getBoundingClientRect().x < 600) {
                return l.href;
            }
        }
        return 'not_found';
    })()
    ''', 2)

    if msg_href == 'not_found':
        print("  Message link not found")
        screenshot(ws, screenshot_name)
        return False

    # Navigate to messaging compose
    send_cmd(ws, 'Page.navigate', {'url': msg_href})
    time.sleep(6)

    # Type message
    escaped = dm_text.replace('\\', '\\\\').replace("'", "\\'")
    type_result = evaluate(ws, f'''
    (() => {{
        var editor = document.querySelector('.msg-form__contenteditable') ||
                     document.querySelector('[contenteditable="true"][aria-label*="Write a message"]');
        if (!editor) return 'editor_not_found';
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('delete');
        document.execCommand('insertText', false, '{escaped}');
        return 'typed:' + editor.innerText.substring(0, 80);
    }})()
    ''', 3)
    print(f"  Type: {type_result}")

    if not type_result or 'not_found' in str(type_result):
        screenshot(ws, screenshot_name)
        return False

    time.sleep(2)

    # Send
    send_result = evaluate(ws, '''
    (() => {
        var btn = document.querySelector('.msg-form__send-button');
        if (btn) { btn.click(); return 'sent'; }
        return 'send_not_found';
    })()
    ''', 4)
    print(f"  Send: {send_result}")

    time.sleep(3)
    screenshot(ws, screenshot_name)

    return 'sent' in str(send_result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: send-dm.py <action>")
        sys.exit(1)

    action = sys.argv[1]
    ws, tab = get_ws()

    dm_specs = {
        'anshul': {
            'url': 'https://www.linkedin.com/in/anshul-jain-%E2%86%97%EF%B8%8F/',
            'search': 'Anshul Jain FrameFry',
            'dm': "Hi Anshul, thanks for connecting! Noticed you run FrameFry Studios and handle post-production for microdramas and ad films. We are The Audio World, a pan-India audio production house. We do VO casting, dubbing, and audio post. If FrameFry ever needs an audio partner for your projects, or if any of your clients need VO and sound work, we would love to collaborate. What kind of projects are you working on right now?",
            'screenshot': '24-anshul-dm.png'
        },
        'vivek': {
            'url': 'https://www.linkedin.com/in/lifeofwake/',
            'search': 'Vivek Bishnoi Mercy Records',
            'dm': "Hi Vivek, thanks for connecting! Saw that Mercy Records does music production, audio post, and content localisation. We are The Audio World, based pan-India, and we work in very similar spaces, voiceovers, dubbing, and audio production. Would love to know what kind of projects Mercy Records is working on. There might be a good overlap where we could support each other.",
            'screenshot': '25-vivek-dm.png'
        },
        'suuresh': {
            'search': 'Suuresh Ramachandran Eye-Q Films',
            'dm': "Hi Suuresh, been connected for a while but never got to introduce myself properly. I am Antara from The Audio World, a pan-India audio production house. We handle VO, dubbing, sound design, and audio post for films, ads, and corporate content. Eye-Q Films has been around for 21 years, that is impressive. If you ever need an audio production partner for any of your projects, would love to discuss.",
            'screenshot': '26-suuresh-dm.png'
        },
        'amitabha': {
            'search': 'Amitabha Singh Film',
            'dm': "Hi Amitabha, thanks for connecting! I am Antara from The Audio World, a pan-India audio production house. We do voiceovers, dubbing, and audio post for films and content projects. What kind of films are you working on these days?",
            'screenshot': '27-amitabha-dm.png'
        },
        'sumit': {
            'search': 'Sumit Pande Podcast',
            'dm': "Hi Sumit, thanks for connecting! I am Antara from The Audio World, we do audio production, VO, and sound design. Podcast production is a sweet spot for us. If you ever need voice talent, audio editing, or mixing for your podcasts, we can help. What shows are you working on?",
            'screenshot': '28-sumit-dm.png'
        },
        'munesh': {
            'search': 'Munesh Chaudhary Casting',
            'dm': "Hi Munesh, thanks for connecting! I am Antara from The Audio World, a pan-India VO and audio production house. We have a large roster of voice artists across Hindi and regional languages. If you ever handle VO casting or need voice talent for projects, we would love to be a resource. What kind of casting are you focused on?",
            'screenshot': '29-munesh-dm.png'
        },
        'kirubakaran': {
            'search': 'KIRUBAKARAN ALBERT Brand Strategist',
            'dm': "Hi Kirubakaran, thanks for connecting! I am Antara from The Audio World, a pan-India audio production house. We handle VO, dubbing, and audio post for brands and agencies. If any of your brand strategy projects need audio or VO work, would love to collaborate. What kind of brands are you working with?",
            'screenshot': '30-kirubakaran-dm.png'
        }
    }

    if action in dm_specs:
        spec = dm_specs[action]
        print(f"Sending DM to {action}...")
        if 'url' in spec:
            result = send_dm_via_profile_url(ws, spec['url'], spec['dm'], spec['screenshot'])
        else:
            result = send_dm_via_profile_search(ws, spec['search'], spec['dm'], spec['screenshot'])
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    else:
        print(f"Unknown action: {action}")

    ws.close()
