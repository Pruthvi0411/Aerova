import os
import sys
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from modules.audio_analyzer import load_audio_signal, generate_spectrogram_and_bars
from modules.models import analyze_cough, MODELS_INFO
from modules.report_generator import generate_pdf_report
from modules.history_manager import load_history, add_record, render_history_dashboard
from modules.robot_copilot import handle_chat, handle_chip

def test_pipeline():
    print("Testing pipeline...")
    
    # 1. Test audio analyzer
    sr, samples, dur, quality, audio_path = load_audio_signal(None, None, None)
    print(f"Audio loaded: sr={sr}, dur={dur}s, quality={quality}")
    assert dur > 0, "Audio duration must be > 0"
    assert os.path.exists(audio_path), "Audio file must exist"

    # 2. Test models
    triage = analyze_cough(
        samples=samples,
        sr=sr,
        symptoms="Dry barking cough for 2 days",
        age=32,
        gender="male",
        confidence_threshold=0.85,
        pre_existing="false",
        fever="false",
        selected_model="extra_trees.joblib"
    )
    print(f"Triage result: {triage['readout']}, risk={triage['risk_tier']}, conf={triage['confidence']}")
    assert triage['readout'] in ["Healthy", "Disease", "Urgent review"]
    assert len(triage['model_table']) == 10

    # 3. Test spectrogram generation
    spec_path = generate_spectrogram_and_bars(
        sr=sr,
        samples=samples,
        prob_healthy=triage["prob_healthy"],
        prob_disease=triage["prob_disease"],
        model_name=triage["model_display_name"]
    )
    print(f"Spectrogram generated: {spec_path} (size={os.path.getsize(spec_path)} bytes)")
    assert os.path.exists(spec_path) and os.path.getsize(spec_path) > 1000

    # 4. Test PDF Report generation
    pdf_path, pdf_uri = generate_pdf_report(
        patient_id="AUR-TEST-001",
        date_str="18 September 2026, 12:45 AM",
        age=32,
        gender="male",
        recipient_email="doctor@hospital-aerova.org",
        triage_data=triage,
        quality_data=quality,
        spectrogram_img_path=spec_path
    )
    print(f"PDF generated: {pdf_path} (size={os.path.getsize(pdf_path)} bytes)")
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000
    assert pdf_uri.startswith("data:application/pdf;base64,")

    # 5. Test history
    add_record("AUR-TEST-001", "18 September 2026, 12:45 AM", triage["readout"], triage["risk_tier"], triage["confidence"])
    hist_html = render_history_dashboard("AUR-TEST")
    print(f"History HTML generated (len={len(hist_html)})")
    assert "AUR-TEST-001" in hist_html

    # 6. Test robot copilot
    hist, _ = handle_chat("What models are used?", [])
    print(f"Robot chat response: {hist[-1]['content'][:80]}...")
    assert len(hist) == 2

    chip_hist, _ = handle_chip("tips", [])
    print(f"Robot chip response: {chip_hist[-1]['content'][:80]}...")
    assert len(chip_hist) == 2

    print("\nALL MODULE TESTS PASSED SUCCESSFULLY! ✓")

if __name__ == "__main__":
    test_pipeline()
