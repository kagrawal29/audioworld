#!/usr/bin/env python3
"""Sprint runner helper for LinkedIn operations via CDP."""

import requests
import json
import websocket
import time
import base64
import sys
import random
import os

CDP_URL = 'http://localhost:9222'
SCREENSHOT_DIR = '/root/Desktop/audioworld/sprint-prep/screenshots/2026-03-20'

def get_tabs():
    """Get all browser tabs."""
    return requests.get(f'{CDP_URL}/json').json()

def get_linkedin_tab():
    """Find the main LinkedIn tab (not protechts, not recaptcha)."""
    tabs = get_tabs()
    for t in tabs:
        url = t.get('url', '')
        if 'linkedin.com' in url and 'protechts' not in url and 'recaptcha' not in url and 'merchantpool' not in url and 'ns1p.net' not in url:
            return t
    return tabs[0]  # fallback

def connect_to_tab(tab_id=None):
    """Connect to a specific tab or the main LinkedIn tab."""
    if tab_id:
        tabs = get_tabs()
        for t in tabs:
            if t['id'] == tab_id:
                ws = websocket.create_connection(t['webSocketDebuggerUrl'])
                send_cmd(ws, 'Page.enable')
                return ws
    tab = get_linkedin_tab()
    ws = websocket.create_connection(tab['webSocketDebuggerUrl'])
    send_cmd(ws, 'Page.enable')
    return ws

def send_cmd(ws, method, params=None, msg_id=None):
    """Send CDP command and return result."""
    if msg_id is None:
        msg_id = random.randint(1000, 99999)
    cmd = {'id': msg_id, 'method': method}
    if params:
        cmd['params'] = params
    ws.send(json.dumps(cmd))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            return resp

def navigate(ws, url, wait=5):
    """Navigate to URL and wait."""
    result = send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(wait)
    return result

def evaluate(ws, expression):
    """Evaluate JS expression and return value."""
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expression,
        'returnByValue': True,
        'awaitPromise': True
    })
    return resp.get('result', {}).get('result', {}).get('value')

def screenshot(ws, name):
    """Take screenshot and save with name."""
    filepath = os.path.join(SCREENSHOT_DIR, f'{name}.png')
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    data = resp.get('result', {}).get('data', '')
    if data:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(data))
        return filepath
    return None

def click_at(ws, x, y):
    """Click at coordinates using CDP mouse events."""
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    })
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    })

def scroll_down(ws, amount=400):
    """Scroll down."""
    evaluate(ws, f'window.scrollBy(0, {amount})')

def scroll_to_top(ws):
    """Scroll to top."""
    evaluate(ws, 'window.scrollTo(0, 0)')

def get_url(ws):
    """Get current page URL."""
    return evaluate(ws, 'window.location.href')

def wait_random(min_sec, max_sec):
    """Wait random time between min and max seconds."""
    t = random.uniform(min_sec, max_sec)
    time.sleep(t)
    return t

def type_in_editor(ws, text):
    """Type text into a contenteditable using execCommand (React-safe)."""
    escaped = text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    return evaluate(ws, f"""
        (() => {{
            const editors = document.querySelectorAll('[contenteditable="true"]');
            let editor = null;
            for (const e of editors) {{
                const rect = e.getBoundingClientRect();
                if (rect.width > 200 && rect.height > 30) {{
                    editor = e;
                    break;
                }}
            }}
            if (!editor) {{
                // Try messaging specific selectors
                editor = document.querySelector('.msg-form__contenteditable') || 
                         document.querySelector('[aria-label*="Write a message"]');
            }}
            if (!editor) return 'NO_EDITOR_FOUND';
            editor.focus();
            document.execCommand('selectAll');
            document.execCommand('delete');
            document.execCommand('insertText', false, '{escaped}');
            return 'OK';
        }})()
    """)

def click_send_button(ws):
    """Click the Send button in messaging."""
    return evaluate(ws, """
        (() => {
            const btn = document.querySelector('.msg-form__send-button');
            if (btn) { btn.click(); return 'CLICKED'; }
            // Fallback: find by aria-label
            const btns = document.querySelectorAll('button[aria-label="Send"]');
            for (const b of btns) {
                if (b.offsetParent !== null) { b.click(); return 'CLICKED_FALLBACK'; }
            }
            return 'NOT_FOUND';
        })()
    """)

if __name__ == '__main__':
    ws = connect_to_tab()
    url = get_url(ws)
    print(f'Connected. Current URL: {url}')
    ws.close()
