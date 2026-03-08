#!/usr/bin/env python3
"""CDP helper for LinkedIn sprint operations."""

import requests
import json
import websocket
import time
import sys
import base64

def get_ws():
    """Get WebSocket connection to first tab."""
    tabs = requests.get('http://localhost:9222/json').json()
    ws_url = tabs[0]['webSocketDebuggerUrl']
    return websocket.create_connection(ws_url)

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
        # Skip events

def navigate(ws, url, wait=5):
    """Navigate to URL and wait."""
    result = send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(wait)
    return result

def evaluate(ws, expression, msg_id=1):
    """Evaluate JS expression and return value."""
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expression,
        'returnByValue': True,
        'awaitPromise': True
    }, msg_id)
    return resp.get('result', {}).get('result', {}).get('value')

def screenshot(ws, filepath):
    """Take a screenshot and save to file."""
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    data = resp.get('result', {}).get('data', '')
    if data:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(data))
        return True
    return False

def click_at(ws, x, y):
    """Click at coordinates."""
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, 10)
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
    }, 11)

def type_text(ws, text):
    """Type text using Input.insertText."""
    send_cmd(ws, 'Input.insertText', {'text': text}, 20)

def scroll_down(ws, amount=300):
    """Scroll down by amount pixels."""
    evaluate(ws, f'window.scrollBy(0, {amount})')

def get_page_info(ws):
    """Get current page title and URL."""
    return evaluate(ws, 'JSON.stringify({title: document.title, url: window.location.href})')
