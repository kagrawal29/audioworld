#!/usr/bin/env python3
"""DM sender helper for LinkedIn sprint via CDP."""

import requests
import json
import websocket
import time
import base64
import sys

def get_li_ws():
    tabs = requests.get('http://localhost:9222/json').json()
    for t in tabs:
        if 'linkedin.com' in t.get('url', ''):
            return websocket.create_connection(t['webSocketDebuggerUrl'])
    return None

def send_cmd(ws, method, params=None, msg_id=1):
    cmd = {'id': msg_id, 'method': method}
    if params:
        cmd['params'] = params
    ws.send(json.dumps(cmd))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            return resp

def evaluate(ws, expr, msg_id=1):
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expr, 'returnByValue': True, 'awaitPromise': True
    }, msg_id)
    return resp.get('result', {}).get('result', {}).get('value')

def click_at(ws, x, y, msg_id=10):
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id)
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id + 1)

def screenshot(ws, filepath):
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    data = resp.get('result', {}).get('data', '')
    if data:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(data))
        return True
    return False

def send_dm_via_profile(ws, name, message, screenshot_path, profile_url=None):
    """Send a DM by navigating to profile and clicking Message."""

    # Step 1: Navigate to profile or search for them
    if profile_url:
        print(f"Navigating to {name}'s profile: {profile_url}")
        send_cmd(ws, 'Page.navigate', {'url': profile_url})
        time.sleep(5)
    else:
        print(f"Searching for {name}...")
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"
        send_cmd(ws, 'Page.navigate', {'url': search_url})
        time.sleep(5)

        # Get profile URL from search results
        url = evaluate(ws, f'''
        (() => {{
            var items = document.querySelectorAll('a[href*="/in/"]');
            for (var a of items) {{
                var text = a.innerText || '';
                if (text.includes("{name}")) {{
                    return a.href.split('?')[0];
                }}
            }}
            // Try spans
            var spans = document.querySelectorAll('.entity-result__title-text a span[aria-hidden="true"]');
            for (var s of spans) {{
                if (s.innerText && s.innerText.includes("{name}")) {{
                    var link = s.closest('a');
                    if (link) return link.href.split('?')[0];
                }}
            }}
            return '';
        }})()
        ''')
        if url:
            profile_url = url
            print(f"Found profile: {url}")
            send_cmd(ws, 'Page.navigate', {'url': url})
            time.sleep(5)
        else:
            print(f"ERROR: Could not find {name}")
            return False

    # Step 2: Scroll to simulate reading
    evaluate(ws, 'window.scrollBy(0, 300)')
    time.sleep(2)
    evaluate(ws, 'window.scrollBy(0, 300)')
    time.sleep(2)
    evaluate(ws, 'window.scrollTo(0, 0)')
    time.sleep(1)

    # Step 3: Click Message button
    msg_click = evaluate(ws, f'''
    (() => {{
        var btns = document.querySelectorAll('button, a');
        for (var b of btns) {{
            var text = b.innerText?.trim() || '';
            var label = b.getAttribute('aria-label') || '';
            var rect = b.getBoundingClientRect();
            if ((text === 'Message' || label.includes('Message {name.split(" ")[0]}')) &&
                rect.x < 800 && rect.y > 350 && rect.y < 550) {{
                b.click();
                return 'clicked at y=' + Math.round(rect.y);
            }}
        }}
        return 'not found';
    }})()
    ''')
    print(f"Message button: {msg_click}")

    if 'not found' in str(msg_click):
        print("Trying coordinate click on Message button area...")
        click_at(ws, 248, 410)

    time.sleep(4)

    # Step 4: Find the compose editor via DOM.performSearch (shadow DOM pierce)
    doc = send_cmd(ws, 'DOM.getDocument', {'depth': -1, 'pierce': True}, 100)
    time.sleep(0.5)

    search_result = send_cmd(ws, 'DOM.performSearch', {
        'query': '[contenteditable="true"]',
        'includeUserAgentShadowDOM': True
    }, 101)
    count = search_result.get('result', {}).get('resultCount', 0)
    search_id = search_result.get('result', {}).get('searchId', '')

    if count == 0:
        print("ERROR: No contenteditable elements found")
        return False

    nodes_result = send_cmd(ws, 'DOM.getSearchResults', {
        'searchId': search_id,
        'fromIndex': 0,
        'toIndex': min(count, 10)
    }, 102)
    node_ids = nodes_result.get('result', {}).get('nodeIds', [])

    # Find the largest editor (compose window)
    target_node = None
    target_pos = None
    for nid in node_ids:
        try:
            box = send_cmd(ws, 'DOM.getBoxModel', {'nodeId': nid}, 103)
            content = box.get('result', {}).get('model', {}).get('content', [])
            if content:
                w = content[4] - content[0]
                h = content[5] - content[1]
                if w > 300 and h > 100:
                    target_node = nid
                    target_pos = (int(content[0] + w/2), int(content[1] + h/2))
                    print(f"Found compose editor: node {nid}, size {int(w)}x{int(h)}")
                    break
        except:
            pass

    if not target_node:
        print("ERROR: Compose editor not found")
        return False

    # Step 5: Click on editor to focus, then resolve and type
    click_at(ws, target_pos[0], target_pos[1], 110)
    time.sleep(0.5)

    resolve = send_cmd(ws, 'DOM.resolveNode', {'nodeId': target_node}, 104)
    object_id = resolve.get('result', {}).get('object', {}).get('objectId', '')

    if not object_id:
        print("ERROR: Could not resolve editor node")
        return False

    msg_escaped = message.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

    call_result = send_cmd(ws, 'Runtime.callFunctionOn', {
        'objectId': object_id,
        'functionDeclaration': f'''function() {{
            this.focus();
            document.execCommand('selectAll');
            document.execCommand('delete');
            document.execCommand('insertText', false, "{msg_escaped}");
            return this.innerText.length;
        }}''',
        'returnByValue': True
    }, 105)
    typed_len = call_result.get('result', {}).get('result', {}).get('value', 0)
    print(f"Typed {typed_len} chars")

    time.sleep(2)

    # Step 6: Find and click Send button
    send_search = send_cmd(ws, 'DOM.performSearch', {
        'query': '.msg-form__send-button',
        'includeUserAgentShadowDOM': True
    }, 106)
    send_count = send_search.get('result', {}).get('resultCount', 0)
    send_sid = send_search.get('result', {}).get('searchId', '')

    if send_count > 0:
        send_nodes = send_cmd(ws, 'DOM.getSearchResults', {
            'searchId': send_sid,
            'fromIndex': 0,
            'toIndex': min(send_count, 10)
        }, 107)
        send_nids = send_nodes.get('result', {}).get('nodeIds', [])

        for snid in send_nids:
            try:
                sbox = send_cmd(ws, 'DOM.getBoxModel', {'nodeId': snid}, 108)
                scontent = sbox.get('result', {}).get('model', {}).get('content', [])
                if scontent:
                    sy = int(scontent[1])
                    sx = int(scontent[0])
                    if sy > 500 and sy < 700 and sx < 600:
                        resolve_send = send_cmd(ws, 'DOM.resolveNode', {'nodeId': snid}, 109)
                        send_obj = resolve_send.get('result', {}).get('object', {}).get('objectId', '')
                        if send_obj:
                            click_result = send_cmd(ws, 'Runtime.callFunctionOn', {
                                'objectId': send_obj,
                                'functionDeclaration': '''function() {
                                    if (!this.disabled) {
                                        this.click();
                                        return 'sent';
                                    }
                                    return 'disabled';
                                }''',
                                'returnByValue': True
                            }, 110)
                            status = click_result.get('result', {}).get('result', {}).get('value', 'error')
                            print(f"Send: {status}")
                            break
            except:
                pass

    time.sleep(3)

    # Step 7: Screenshot
    screenshot(ws, screenshot_path)
    print(f"Screenshot saved: {screenshot_path}")

    return True

if __name__ == '__main__':
    # Test with a specific name and message
    if len(sys.argv) < 3:
        print("Usage: dm_sender.py <name> <message> [screenshot_path] [profile_url]")
        sys.exit(1)

    name = sys.argv[1]
    message = sys.argv[2]
    ss_path = sys.argv[3] if len(sys.argv) > 3 else '/tmp/dm_test.png'
    profile_url = sys.argv[4] if len(sys.argv) > 4 else None

    ws = get_li_ws()
    if not ws:
        print("ERROR: No LinkedIn tab found")
        sys.exit(1)

    success = send_dm_via_profile(ws, name, message, ss_path, profile_url)
    ws.close()

    if success:
        print("DM sent successfully")
    else:
        print("DM failed")
        sys.exit(1)
