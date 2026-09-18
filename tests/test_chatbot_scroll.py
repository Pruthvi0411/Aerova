import asyncio
import json
import subprocess
import time
import urllib.request
import websockets
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
APP_URL = "http://127.0.0.1:7860/"

async def run_test():
    # Cleanup previous chrome debug instances
    subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | Where-Object CommandLine -match 'remote-debugging-port=9222' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"], capture_output=True)
    time.sleep(1)

    user_data = r"C:\Users\Pruthvi\AppData\Local\Temp\chrome_test_profile"
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        f"--user-data-dir={user_data}",
        "--window-size=1280,900",
        APP_URL
    ])
    
    time.sleep(3)
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list")
        tabs = json.loads(req.read().decode())
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        assert len(page_tabs) > 0, "No page tab found in Chrome!"
        tab_info = page_tabs[0]
        ws_url = tab_info["webSocketDebuggerUrl"]
        print(f"Connected to page tab '{tab_info.get('title')}':", ws_url, flush=True)

        async with websockets.connect(ws_url) as ws:
            msg_id = 0
            async def send_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    res = json.loads(await ws.recv())
                    if res.get("id") == payload["id"]:
                        return res.get("result", {})

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await asyncio.sleep(3)

            # Click 1-click Demo Login
            login_res = await send_cmd("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const btn = document.querySelector('.demo-fast-btn') || Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Instant Demo'));
                        if (btn) {
                            btn.click();
                            return 'CLICKED_DEMO_BTN: ' + btn.textContent.trim();
                        }
                        return 'BTN_NOT_FOUND';
                    })()
                """
            })
            print("Login click:", login_res.get("result", {}).get("value"), flush=True)
            await asyncio.sleep(2)

            # Open robot copilot dock accordion
            open_acc_res = await send_cmd("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const dock = document.querySelector('.robot-dock');
                        if (!dock) return 'DOCK_NOT_FOUND';
                        const accHeader = dock.querySelector('.label-wrap, button, .icon') || Array.from(dock.querySelectorAll('*')).find(el => el.textContent && el.textContent.includes('AEROVA-BOT PRO'));
                        if (accHeader) {
                            accHeader.click();
                            return 'CLICKED_ROBOT_ACCORDION';
                        }
                        return 'ACC_HEADER_NOT_FOUND';
                    })()
                """
            })
            print("Open dock accordion:", open_acc_res.get("result", {}).get("value"), flush=True)
            await asyncio.sleep(2)

            # Click prompt chips to populate message history
            for chip_text in ["Recording Tips", "ML Models", "Result Meaning", "PDF Reports"]:
                chip_res = await send_cmd("Runtime.evaluate", {
                    "expression": f"""
                        (function() {{
                            const chip = Array.from(document.querySelectorAll('.robot-chip, button')).find(b => b.textContent.includes('{chip_text}'));
                            if (chip) {{
                                chip.click();
                                return 'CLICKED_{chip_text}';
                            }}
                            return 'NOT_FOUND';
                        }})()
                    """
                })
                print(f"Chip {chip_text}:", chip_res.get("result", {}).get("value"))
                await asyncio.sleep(1)

            # Check messages populated and scroll status
            scroll_info = await send_cmd("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const scrollable = document.querySelector('#aerova-robot-chatbot .bubble-wrap, #aerova-robot-chatbot [class*="bubble-wrap"], #aerova-robot-chatbot [class*="panel-wrap"]');
                        let rect = scrollable ? scrollable.getBoundingClientRect() : null;
                        return {
                            clientHeight: scrollable ? scrollable.clientHeight : 0,
                            scrollHeight: scrollable ? scrollable.scrollHeight : 0,
                            scrollTop: scrollable ? scrollable.scrollTop : 0,
                            rect: rect ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height } : null
                        };
                    })()
                """,
                "returnByValue": True
            })
            sc_val = scroll_info.get("result", {}).get("value", {})
            print("Chatbot scroll measurements:", json.dumps(sc_val, indent=2))
            assert sc_val["scrollHeight"] > sc_val["clientHeight"], f"Expected scrollHeight > clientHeight, got {sc_val}"

            # Test mouse wheel scrolling
            rect = sc_val.get("rect")
            mid_x = rect["x"] + rect["width"] / 2
            mid_y = rect["y"] + rect["height"] / 2
            
            # Wheel UP
            await send_cmd("Input.dispatchMouseEvent", {
                "type": "mouseWheel",
                "x": mid_x,
                "y": mid_y,
                "deltaX": 0,
                "deltaY": -300
            })
            await asyncio.sleep(0.5)

            after_wheel_up = await send_cmd("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const s = document.querySelector('#aerova-robot-chatbot .bubble-wrap, #aerova-robot-chatbot [class*="bubble-wrap"]');
                        return { scrollTop: s.scrollTop, scrollHeight: s.scrollHeight, clientHeight: s.clientHeight };
                    })()
                """,
                "returnByValue": True
            })
            up_val = after_wheel_up.get("result", {}).get("value", {})
            print("After wheel UP:", up_val)
            assert up_val["scrollTop"] < sc_val["scrollTop"], "Expected scrollTop to decrease after wheel UP!"

            # Wheel DOWN
            await send_cmd("Input.dispatchMouseEvent", {
                "type": "mouseWheel",
                "x": mid_x,
                "y": mid_y,
                "deltaX": 0,
                "deltaY": 300
            })
            await asyncio.sleep(0.5)

            after_wheel_down = await send_cmd("Runtime.evaluate", {
                "expression": """
                    (function() {
                        const s = document.querySelector('#aerova-robot-chatbot .bubble-wrap, #aerova-robot-chatbot [class*="bubble-wrap"]');
                        return { scrollTop: s.scrollTop, scrollHeight: s.scrollHeight, clientHeight: s.clientHeight };
                    })()
                """,
                "returnByValue": True
            })
            down_val = after_wheel_down.get("result", {}).get("value", {})
            print("After wheel DOWN:", down_val)
            assert down_val["scrollTop"] > up_val["scrollTop"], "Expected scrollTop to increase after wheel DOWN!"

            print("\n==========================================")
            print("CHATBOT SCROLLING TEST PASSED PERFECTLY! ✓")
            print("==========================================")

    finally:
        chrome_proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_test())
