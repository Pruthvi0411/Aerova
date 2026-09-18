import json
import os
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")

def load_history():
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(records):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

def add_record(patient_id, date_str, readout, risk, confidence, model="extra_trees.joblib", age=30, gender="unknown"):
    records = load_history()
    new_entry = {
        "patient_id": patient_id,
        "date": date_str,
        "readout": readout,
        "risk": risk,
        "confidence": confidence,
        "model": model,
        "age": age,
        "gender": gender
    }
    # Prepend to the top of the list
    records.insert(0, new_entry)
    save_history(records)
    return records

def render_history_dashboard(search_query=""):
    records = load_history()
    query = (search_query or "").strip().upper()

    if query:
        filtered = [r for r in records if query in r.get("patient_id", "").upper()]
    else:
        filtered = records

    total = len(records)
    flagged = sum(1 for r in records if r.get("readout", "").lower() not in ["healthy", "normal"])
    high_risk = sum(1 for r in records if r.get("risk", "").lower() == "high")

    rows_html = ""
    if not filtered:
        rows_html = '<tr><td colspan="5" class="history-empty">No matching assessments yet.</td></tr>'
    else:
        for r in filtered:
            pid = r.get("patient_id", "")
            date = r.get("date", "")
            readout = r.get("readout", "")
            risk = r.get("risk", "")
            conf = r.get("confidence", "")
            rows_html += f"<tr><td><b>{pid}</b></td><td>{date}</td><td>{readout}</td><td>{risk}</td><td>{conf}</td></tr>"

    return f"""<div class="history-dashboard">
      <div class="history-metrics">
        <div><span>Total assessments</span><strong>{total}</strong></div>
        <div><span>Flagged results</span><strong>{flagged}</strong></div>
        <div><span>High-risk cases</span><strong>{high_risk}</strong></div>
      </div>
      <div class="history-table-wrap"><table class="history-table">
        <thead><tr><th>Patient ID</th><th>Date</th><th>Readout</th><th>Risk</th><th>Confidence</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table></div>
    </div>"""
