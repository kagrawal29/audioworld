#!/usr/bin/env python3
"""Sales Nav CR sender - batch mode."""

import requests
import json
import websocket
import time
import base64
import os
import sys

SCREENSHOTS_DIR = '/root/Desktop/audioworld/sprint-prep/screenshots/2026-03-23'
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_ws():
    """Get WebSocket to a LinkedIn/Sales Nav tab."""
    tabs = requests.get('http://localhost:9222/json').json()
    for t in tabs:
        if 'linkedin.com/sales' in t['url'] or 'linkedin.com/in/' in t['url'] or 'linkedin.com/feed' in t['url']:
            if 'protechts' not in t['url'] and 'merchantpool' not in t['url']:
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

def click_at(ws, x, y, msg_id=10):
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id)
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id + 1)

def send_salesnav_cr(ws, search_query, cr_note, screenshot_name):
    """Search for person in Sales Nav, navigate to lead page, send CR with note."""

    # Step 1: Search in Sales Nav
    from urllib.parse import quote
    search_url = f'https://www.linkedin.com/sales/search/people?query=(keywords%3A{quote(search_query)})'
    send_cmd(ws, 'Page.navigate', {'url': search_url})
    time.sleep(8)

    # Step 2: Find lead link
    lead_url = evaluate(ws, '''
    (() => {
        var spans = document.querySelectorAll('span[data-anonymize="person-name"]');
        var links = document.querySelectorAll('a[href*="/sales/lead/"]');
        if (links.length > 0) {
            // Get the first lead link that has visible text
            for (var l of links) {
                if (l.innerText.trim().length > 2) {
                    return l.href;
                }
            }
            return links[0].href;
        }
        return 'not_found';
    })()
    ''', 2)

    if lead_url == 'not_found':
        print(f"  Lead not found in search for: {search_query}")
        return False

    print(f"  Lead URL: {lead_url[:80]}")

    # Step 3: Navigate to lead profile
    send_cmd(ws, 'Page.navigate', {'url': lead_url})
    time.sleep(7)

    title = evaluate(ws, 'document.title', 3)
    print(f"  Page: {title}")

    # Step 4: Click overflow menu
    overflow = evaluate(ws, '''
    (() => {
        var btn = document.querySelector('[aria-label="Open actions overflow menu"]');
        if (!btn) return 'not_found';
        var rect = btn.getBoundingClientRect();
        return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)});
    })()
    ''', 4)

    if overflow == 'not_found':
        print("  Overflow menu not found")
        screenshot(ws, screenshot_name)
        return False

    coords = json.loads(overflow)
    click_at(ws, coords['x'], coords['y'], 20)
    time.sleep(2)

    # Step 5: Find and click Connect
    connect = evaluate(ws, '''
    (() => {
        var btns = document.querySelectorAll('button, [role="menuitem"]');
        for (var b of btns) {
            var txt = b.innerText.trim();
            var rect = b.getBoundingClientRect();
            if (txt === 'Connect' && rect.width > 50) {
                return JSON.stringify({x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)});
            }
        }
        // Check if already connected or pending
        var allBtns = [];
        for (var b of btns) {
            var txt = b.innerText.trim();
            var rect = b.getBoundingClientRect();
            if (rect.width > 50 && rect.height > 10 && txt.length > 0 && txt.length < 30) {
                allBtns.push(txt);
            }
        }
        return 'not_found:' + JSON.stringify(allBtns);
    })()
    ''', 5)

    if 'not_found' in str(connect):
        print(f"  Connect not in menu: {connect}")
        screenshot(ws, screenshot_name)
        return False

    coords = json.loads(connect)
    click_at(ws, coords['x'], coords['y'], 30)
    time.sleep(3)

    # Step 6: Fill in note
    escaped_note = cr_note.replace('\\', '\\\\').replace("'", "\\'")
    note_result = evaluate(ws, f'''
    (() => {{
        var textarea = document.querySelector('[role="dialog"] textarea');
        if (!textarea) {{
            var tas = document.querySelectorAll('textarea');
            for (var ta of tas) {{
                if (ta.offsetParent !== null) {{ textarea = ta; break; }}
            }}
        }}
        if (!textarea) return 'textarea_not_found';
        textarea.focus();
        textarea.value = '{escaped_note}';
        textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
        return 'note_set:' + textarea.value.length + ' chars';
    }})()
    ''', 6)
    print(f"  Note: {note_result}")

    if 'not_found' in str(note_result):
        screenshot(ws, screenshot_name)
        return False

    time.sleep(1)

    # Step 7: Click Send Invitation
    send_result = evaluate(ws, '''
    (() => {
        var btns = document.querySelectorAll('[role="dialog"] button, button');
        for (var b of btns) {
            var txt = b.innerText.trim().toLowerCase();
            if (txt.includes('send invitation') || txt.includes('send invite')) {
                b.click();
                return 'sent';
            }
        }
        return 'send_not_found';
    })()
    ''', 7)
    print(f"  Send: {send_result}")

    time.sleep(3)
    screenshot(ws, screenshot_name)

    return 'sent' in str(send_result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: salesnav-cr.py <action>")
        print("Actions: mayank, neeraj, sriti, abhishek, imran, mohak, sikandar, shaardul")
        print("         ahmed, pushpender, summit, rudra, sean, abhijeet")
        sys.exit(1)

    action = sys.argv[1]
    ws, tab = get_ws()

    cr_specs = {
        'mayank': {
            'query': 'Mayank Sharma bookmyvoartist',
            'note': "Hi Mayank, saw your post about needing a male English VO artist. We are The Audio World, a pan-India VO and audio production house. We can help with this and future requirements. Let me know if you want samples.",
            'screenshot': '08-mayank-cr.png'
        },
        'neeraj': {
            'query': 'Neeraj Charmkar JP Translation',
            'note': "Hi Neeraj, saw your urgent Telugu dubbing requirement. We are The Audio World and handle dubbing in Telugu and 10+ Indian languages. Quick turnaround, clean audio delivery. Happy to discuss.",
            'screenshot': '09-neeraj-cr.png'
        },
        'sriti': {
            'query': 'Sriti Biswas EchoLens',
            'note': "Hi Sriti, saw your post about EchoLens Studio looking for VO artists. We are The Audio World, a full-service audio production house. If you ever need a production partner for bigger projects or bulk VO work, we would love to collaborate.",
            'screenshot': '10-sriti-cr.png'
        },
        'abhishek': {
            'query': 'Abhishek Maji Majik House',
            'note': "Hi Abhishek, saw your post about The Majik House and the work you have done with brands like Groww and Pocket FM. We are The Audio World, a pan-India audio production house. Would be great to connect and explore if we can add value to your audio production needs.",
            'screenshot': '11-abhishek-cr.png'
        },
        'imran': {
            'query': 'Imran Shamsi What Works',
            'note': "Hi Imran, loved the WWE x STRT91 film about the Mumbai kid finding hip-hop through John Cena. That localisation approach is exactly what we do at The Audio World for audio. Would be great to connect.",
            'screenshot': '12-imran-cr.png'
        },
        'mohak': {
            'query': 'Mohak Gadhok JioStar',
            'note': "Hi Mohak, your work in branded content at JioStar caught my attention. We are The Audio World, a pan-India VO and audio production house. We handle dubbing, VO casting, and audio post for branded content and OTT. Would love to connect.",
            'screenshot': '13-mohak-cr.png'
        },
        'sikandar': {
            'query': 'Sikandar Nawaz Rajput',
            'note': "Hi Sikandar, saw your Lumu campaign post, the way you balanced TVC quality with social media relatability was well done. We are The Audio World, handling VO, dubbing, and audio post for ad films and digital campaigns across India. Would love to connect.",
            'screenshot': '14-sikandar-cr.png'
        },
        'shaardul': {
            'query': 'Shaardul Patthare NINE NINETY',
            'note': "Hi Shaardul, saw your comment on Aryemann's audio production post. We are The Audio World, a pan-India audio house handling VO, dubbing, sound design, and mastering. Looks like 990 Productions could use an audio partner. Let's connect.",
            'screenshot': '15-shaardul-cr.png'
        },
        'ahmed': {
            'query': 'Ahmed Khan Imagine Media Producer',
            'note': "Hi Ahmed, your branded content work at Imagine Media and the ITC Sunfeast film caught my eye. We are The Audio World, handling VO, sound design, and audio post for ad films and branded content across India. Would be great to connect.",
            'screenshot': '16-ahmed-cr.png'
        },
        'pushpender': {
            'query': 'pushpender jeet lal OneSetVision',
            'note': "Hi Pushpender, your work at OneSetVision across ad films, corporate videos, and explainer content is impressive. We are The Audio World, a pan-India audio house. We do VO, dubbing, and sound design for exactly these formats. Happy to connect.",
            'screenshot': '17-pushpender-cr.png'
        },
        'summit': {
            'query': 'Summit Studio Dialogbox Creative',
            'note': "Hi Summit, saw your work at Studio Dialogbox. We are The Audio World, a pan-India audio production house handling VO, dubbing, and sound design for creative agencies and production houses. Would love to connect and explore how we can work together.",
            'screenshot': '18-summit-cr.png'
        },
        'rudra': {
            'query': 'Rudra Dasgupta Director Creative Head',
            'note': "Hi Rudra, your 24 years in TV and OTT post-production is impressive. We are The Audio World, handling VO, dubbing, and audio post for OTT and web content. If you ever need a reliable audio partner for your projects, would love to connect.",
            'screenshot': '19-rudra-cr.png'
        },
        'sean': {
            'query': 'Sean Tahan Director Creative Producer Telangana',
            'note': "Hi Sean, your 9 years in video production and creative direction across campaigns is solid work. We are The Audio World, a pan-India audio production house. We handle VO, dubbing, and audio post for films and campaigns. Would love to connect.",
            'screenshot': '20-sean-cr.png'
        },
        'abhijeet': {
            'query': 'Abhijeet Senior Creative Producer K12',
            'note': "Hi Abhijeet, your creative production work spanning entertainment and edtech is interesting. We are The Audio World, handling VO, dubbing, and audio post for films, series, and branded content. If you need an audio partner, let us connect.",
            'screenshot': '21-abhijeet-cr.png'
        }
    }

    if action in cr_specs:
        spec = cr_specs[action]
        print(f"Sending CR to {action}...")
        result = send_salesnav_cr(ws, spec['query'], spec['note'], spec['screenshot'])
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    else:
        print(f"Unknown action: {action}")

    ws.close()
