#!/usr/bin/env python3
"""Sprint runner for 2026-03-23 Tier 1 sprint."""

import requests
import json
import websocket
import time
import base64
import sys
import os

SCREENSHOTS_DIR = '/root/Desktop/audioworld/sprint-prep/screenshots/2026-03-23'
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_tab(url_contains=None):
    """Get a LinkedIn tab."""
    tabs = requests.get('http://localhost:9222/json').json()
    if url_contains:
        for t in tabs:
            if url_contains in t['url']:
                return t
    # Return first LinkedIn tab
    for t in tabs:
        if 'linkedin.com' in t['url'] and 'protechts' not in t['url'] and 'merchantpool' not in t['url'] and 'ns1p.net' not in t['url']:
            return t
    return tabs[0]

def get_ws(tab=None, url_contains=None):
    """Get WebSocket connection to a tab."""
    if tab is None:
        tab = get_tab(url_contains)
    return websocket.create_connection(tab['webSocketDebuggerUrl']), tab

def send_cmd(ws, method, params=None, msg_id=1):
    """Send CDP command and return result."""
    cmd = {'id': msg_id, 'method': method}
    if params:
        cmd['params'] = params
    ws.send(json.dumps(cmd))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            return resp

def evaluate(ws, expression, msg_id=1):
    """Evaluate JS expression and return value."""
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expression,
        'returnByValue': True,
        'awaitPromise': True
    }, msg_id)
    return resp.get('result', {}).get('result', {}).get('value')

def navigate(ws, url, wait=6):
    """Navigate to URL and wait."""
    result = send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(wait)
    return result

def screenshot(ws, filename):
    """Take a screenshot."""
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    data = resp.get('result', {}).get('data', '')
    if data:
        path = os.path.join(SCREENSHOTS_DIR, filename)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data))
        return path
    return None

def click_at(ws, x, y, msg_id=10):
    """Click at coordinates."""
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id)
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, msg_id + 1)

def post_comment(ws, comment_text):
    """Post a comment on the current post page."""
    # Check if editor is already open, if not click Comment button
    result = evaluate(ws, '''
    (() => {
        var editor = document.querySelector('[aria-label="Text editor for creating content"]');
        if (editor) return 'already_open';
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.innerText.trim() === 'Comment' && !b.closest('.comments-comment-box')) {
                b.scrollIntoView({behavior: 'smooth', block: 'center'});
                return 'need_click';
            }
        }
        return 'no_button';
    })()
    ''')

    if result == 'need_click':
        time.sleep(1)
        evaluate(ws, '''
        (() => {
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                if (b.innerText.trim() === 'Comment' && !b.closest('.comments-comment-box')) {
                    b.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        })()
        ''')
        time.sleep(2)
    elif result == 'no_button':
        print("ERROR: No Comment button found on page")
        return False

    # Type the comment
    # Escape the text for JS
    escaped = comment_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    type_result = evaluate(ws, f'''
    (() => {{
        var editor = document.querySelector('[aria-label="Text editor for creating content"]');
        if (!editor) return 'editor_not_found';
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('delete');
        document.execCommand('insertText', false, '{escaped}');
        return 'typed:' + editor.innerText.substring(0, 80);
    }})()
    ''')
    print(f"Type result: {type_result}")

    if not type_result or 'editor_not_found' in str(type_result):
        print("ERROR: Editor not found")
        return False

    time.sleep(2)

    # Find and click submit button
    submit_result = evaluate(ws, '''
    (() => {
        // Try multiple approaches to find submit
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            var cls = b.className || '';
            if (cls.includes('comment-box__submit')) {
                b.click();
                return 'submitted_via_class';
            }
        }
        // Try by text inside comment box
        var commentBox = document.querySelector('.comments-comment-box, [class*="comments-comment-box"]');
        if (commentBox) {
            var cbtns = commentBox.querySelectorAll('button');
            for (var cb of cbtns) {
                if (cb.innerText.trim() === 'Comment' || cb.innerText.trim() === 'Post') {
                    cb.click();
                    return 'submitted_via_text';
                }
            }
        }
        // List all buttons for debugging
        var all = [];
        for (var b of btns) {
            if (b.offsetParent !== null) { // visible only
                all.push(b.className.substring(0, 60) + ' | ' + b.innerText.trim().substring(0, 30));
            }
        }
        return 'not_found: ' + JSON.stringify(all.slice(-10));
    })()
    ''')
    print(f"Submit result: {submit_result}")

    if submit_result and 'submitted' in str(submit_result):
        time.sleep(3)
        return True

    return False


def send_dm_from_profile(ws, dm_text, person_name):
    """Send a DM by clicking Message on profile page, then typing in the messaging page."""
    # Click the Message button on the profile
    msg_result = evaluate(ws, '''
    (() => {
        var btns = document.querySelectorAll('button, a');
        for (var b of btns) {
            var txt = b.innerText.trim();
            var label = b.getAttribute('aria-label') || '';
            if (txt === 'Message' && b.getBoundingClientRect().x < 800 && b.getBoundingClientRect().width > 30) {
                b.click();
                return 'clicked_message';
            }
            if (label.includes('Message') && b.getBoundingClientRect().x < 800) {
                b.click();
                return 'clicked_message_aria';
            }
        }
        return 'no_message_button';
    })()
    ''')
    print(f"Message button: {msg_result}")

    if 'no_message' in str(msg_result):
        return False

    time.sleep(4)

    # Check if we're on /messaging/ page or overlay
    url = evaluate(ws, 'window.location.href')
    print(f"Current URL: {url}")

    if '/messaging/' in str(url):
        # Full messaging page - standard selectors work
        escaped = dm_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
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
        ''')
        print(f"DM type result: {type_result}")

        if not type_result or 'not_found' in str(type_result):
            return False

        time.sleep(2)

        # Click send
        send_result = evaluate(ws, '''
        (() => {
            var btn = document.querySelector('.msg-form__send-button');
            if (btn) { btn.click(); return 'sent'; }
            return 'send_not_found';
        })()
        ''')
        print(f"DM send result: {send_result}")
        return 'sent' in str(send_result)
    else:
        # Overlay - need shadow DOM pierce
        print("Overlay detected - will need shadow DOM approach")
        return False


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'test'

    if action == 'comment_aryemann_agency':
        ws, tab = get_ws(url_contains='feed/update')
        comment = "Hi Aryemann, we are a pan-India audio production house with in-house writers, voice artists, and sound engineers. Quick turnaround is what we do best. Sent you a DM."
        result = post_comment(ws, comment)
        print(f"\nComment posted: {result}")
        if result:
            time.sleep(2)
            screenshot(ws, '02-aryemann-agency-comment.png')
            print("Screenshot saved")
        ws.close()

    elif action == 'test':
        ws, tab = get_ws()
        print(f"Connected to: {tab['url'][:80]}")
        title = evaluate(ws, 'document.title')
        print(f"Title: {title}")
        ws.close()
