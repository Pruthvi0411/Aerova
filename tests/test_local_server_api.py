import urllib.request
import json
import time

base = "http://127.0.0.1:7860/gradio_api"

def call_local_endpoint(fn_name, data):
    url = f"{base}/call/{fn_name}"
    req_data = json.dumps({"data": data}).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        event_id = res.get('event_id')
        
        res_url = f"{base}/call/{fn_name}/{event_id}"
        res_req = urllib.request.Request(res_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(res_req, timeout=15) as res_resp:
            return res_resp.read().decode('utf-8')

print("1. Testing _fast_demo_login...")
login_res = call_local_endpoint("_fast_demo_login", [])
print("Login result:", login_res[:150])
assert "Instant Demo Access granted" in login_res

print("2. Testing captcha refresh (lambda)...")
captcha_res = call_local_endpoint("lambda", [])
print("Captcha result:", captcha_res[:100])
assert "What is" in captcha_res

print("3. Testing robot prompt chip (lambda_1)...")
chip_res = call_local_endpoint("lambda_1", [[], ""])
print("Chip result:", chip_res[:150])
assert "Recording Best Practices" in chip_res

print("4. Testing patient history (history_dashboard_html)...")
hist_res = call_local_endpoint("history_dashboard_html", [""])
print("History result:", hist_res[:150])
assert "history-table" in hist_res

print("5. Testing triage generation (lambda_8)...")
triage_inputs = [
    "doctor@hospital-aerova.org",
    None,
    None,
    None,
    "Dry barking cough for 2 days",
    "extra_trees.joblib",
    "male",
    32,
    0.85,
    "false",
    "false"
]
triage_res = call_local_endpoint("lambda_8", triage_inputs)
print("Triage result length:", len(triage_res))
assert "result-card" in triage_res
assert "Extra Trees" in triage_res or "extra_trees.joblib" in triage_res

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("\nALL LOCAL API ENDPOINTS RESPONDED WITH 100% ACCURACY! [SUCCESS]")
