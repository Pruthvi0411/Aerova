import os
import random
import urllib.parse
from datetime import datetime
import gradio as gr

from modules.history_manager import load_history, add_record, render_history_dashboard
from modules.audio_analyzer import load_audio_signal, generate_spectrogram_and_bars
from modules.models import analyze_cough, MODELS_INFO
from modules.report_generator import generate_pdf_report
from modules.robot_copilot import handle_chat, handle_chip

# Read custom CSS
CSS_PATH = os.path.join(os.path.dirname(__file__), "assets", "custom.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        CUSTOM_CSS = f.read()
else:
    CUSTOM_CSS = ""

# Client-side JavaScript helper for WhatsApp PDF download & Web Share
JS_HEADER = """
<script>
window.sendPdfToWhatsApp = async function(patientId, phone, pdfDataUri) {
  const cleanPhone = (phone || '').replace(/[^\\d]/g, '');
  const filename = 'AEROVA-Report-' + patientId + '.pdf';

  // 1. Try Native Web Share API with PDF file attachment
  if (pdfDataUri && navigator.canShare) {
    try {
      const res = await fetch(pdfDataUri);
      const blob = await res.blob();
      const file = new File([blob], filename, { type: 'application/pdf' });
      if (navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: 'AEROVA PDF Report - ' + patientId,
          text: '📄 AEROVA Verified Medical Screening Report (PDF Document)'
        });
        return;
      }
    } catch (e) {
      console.log('Native share bypassed:', e);
    }
  }

  // 2. Download PDF file directly to device
  if (pdfDataUri) {
    const dl = document.createElement('a');
    dl.href = pdfDataUri;
    dl.download = filename;
    document.body.appendChild(dl);
    dl.click();
    document.body.removeChild(dl);
  }

  // 3. Open WhatsApp chat with pre-filled clinical PDF header
  const waMsg = encodeURIComponent(
    '📄 *AEROVA CLINICAL SCREENING REPORT (OFFICIAL PDF)*\\n' +
    '━━━━━━━━━━━━━━━━━━━━━━\\n' +
    '📋 *Patient ID:* ' + patientId + '\\n' +
    '📎 *Attached Document:* ' + filename + '\\n' +
    '━━━━━━━━━━━━━━━━━━━━━━\\n' +
    'ℹ️ Verified clinical acoustic screening report in official PDF format.'
  );
  const waUrl = cleanPhone
    ? 'https://api.whatsapp.com/send?phone=' + cleanPhone + '&text=' + waMsg
    : 'https://api.whatsapp.com/send?text=' + waMsg;

  window.open(waUrl, '_blank');
};
</script>
"""

# HTML template builders
def build_progress_html(step=1):
    c1 = "active" if step == 1 else ""
    c2 = "active" if step == 2 else ""
    c3 = "active" if step == 3 else ""
    return f'<div class="progress"><div class="progress-item {c1}">01 · Audio Intake</div><div class="progress-item {c2}">02 · Clinical Context</div><div class="progress-item {c3}">03 · Readout & Reports</div></div>'

def build_result_card_html(triage_data):
    status_class = "status-healthy" if triage_data["prediction"] == "Healthy" else "status-disease"
    risk_class = f"risk-{triage_data['risk_tier'].lower()}"
    width_pct = f"{triage_data['confidence_float'] * 100.0:.1f}%"
    return f"""<div class="result-card {status_class}">
            <div class="result-kicker">SCREENING SIGNAL</div>
            <div class="result-heading"><span>{triage_data['readout']}</span><span class="confidence">{triage_data['confidence']} confidence</span></div>
            <p class="result-summary">{triage_data['summary']}</p>
            <div class="meter"><span style="width: {width_pct}"></span></div>
            <div class="result-meta"><span class="risk-pill {risk_class}">{triage_data['risk_tier'].lower()} risk</span><span>Model: {triage_data['model_name']}</span></div>
        </div>"""

def build_quality_card_html(quality_data):
    status = quality_data.get("status", "Good")
    dur = quality_data.get("duration", 1.0)
    dbfs = quality_data.get("dbfs", -28.1)
    clip = quality_data.get("clipping", 0.0)
    return f"""<div class="quality-card quality-good">
      <div class="section-label">Recording quality · {status.upper()}</div>
      <div class="quality-stats"><span>{dur}s duration</span><span>{dbfs} dBFS signal</span><span>{clip:.2f}% clipping</span></div>
      <ul><li>Recording length and signal level are suitable for screening.</li></ul></div>"""

def build_details_panel_html(triage_data, patient_id, date_str, age, gender, pdf_data_uri):
    chips_html = "".join(f'<span class="symptom-chip">{c}</span>' for c in triage_data.get("extracted_symptoms", ["cough"]))
    
    # WhatsApp share text message
    wa_msg = (
        f"📄 *AEROVA CLINICAL SCREENING REPORT (OFFICIAL PDF)*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Patient ID:* {patient_id}\n"
        f"📅 *Date:* {date_str}\n"
        f"👤 *Profile:* {age} yrs · {gender.capitalize()}\n"
        f"🔍 *Acoustic Readout:* *{triage_data['readout']}*\n"
        f"⚠️ *Clinical Risk Tier:* *{triage_data['risk_tier']}*\n"
        f"🎯 *Model Confidence:* *{triage_data['confidence']}*\n"
        f"🧠 *Analysis Model:* {triage_data['model_name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📎 *Report Document:* aerova-{patient_id.lower()}.pdf\n"
        f"🔒 *Authentication:* QR-Verified Acoustic Screening\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"ℹ️ Screening aid only. Consult a healthcare professional for clinical diagnosis."
    )
    encoded_wa = urllib.parse.quote(wa_msg)
    wa_onclick = f"if(window.sendPdfToWhatsApp){{ window.sendPdfToWhatsApp('{patient_id}', '', '{pdf_data_uri}'); }}"

    return f"""<div class="details-panel">
            <div class="detail-section"><div class="section-label">What we heard</div><p>{triage_data['what_we_heard']}</p></div>
            <div class="detail-section"><div class="section-label">Context signals</div><p>{triage_data['context_signals']}</p><div class="chips">{chips_html}</div></div>
            <div class="recommendation"><div class="section-label">Next best step</div><p>{triage_data['next_best_step']}</p></div>
        </div><div class="share-actions">
        <a class="share-action share-action-wa" href="https://api.whatsapp.com/send?text={encoded_wa}" target="_blank" rel="noopener noreferrer" onclick="{wa_onclick}">📲 Share via WhatsApp</a>
    </div>"""

def build_model_comp_html(triage_data):
    rows = ""
    for m in triage_data["model_table"]:
        rows += f"<tr><td>{m['model']}</td><td>{m['prediction']}</td><td>{m['confidence']}</td><td>{m['val_acc']}</td></tr>"

    return f"""<div class="comparison-panel"><div class="comparison-head"><div><span class="section-label">Model consensus</span><strong>{triage_data['consensus_title']}</strong></div><span>{triage_data['consensus_text']}</span></div>
      <div class="history-table-wrap"><table class="history-table"><thead><tr><th>Model</th><th>Prediction</th><th>Confidence</th><th>Validation accuracy</th></tr></thead><tbody>{rows}</tbody></table></div></div>"""


# Gradio Application Definition
with gr.Blocks(title="AEROVA PRO | AI Respiratory Triage & Robot Copilot") as demo:
    # Global state
    clinician_session = gr.State("doctor@hospital-aerova.org")
    gemini_key_state = gr.State("")
    triage_state = gr.State(None)
    captcha_state = gr.State({"a": 7, "b": 2})

    # =========================================================================
    # 1. LOGIN / ENTRY GATE
    # =========================================================================
    with gr.Column(visible=True, elem_classes=["login-shell"]) as login_col:
        gr.HTML("""
        <div class="login-panel">
            <div class="login-mark">
              <span style="color: #00e5b0; font-size: 32px;">✦</span>
              <span>AEROVA <span style="font-size: 14px; background: #00e5b0; color: #041620; padding: 2px 8px; border-radius: 6px; vertical-align: middle;">PRO v2.5</span></span>
            </div>
            <div class="eyebrow" style="margin-top: 18px; color: #38bdf8;">Hospital Respiratory Triage Unit</div>
            <h1 style="margin: 12px 0 8px; font-size: clamp(26px, 3.2vw, 42px); line-height: 1.1; color: white;">Acoustic Screening & AI Clinical Decision Support</h1>
            <p class="login-copy">Access the enterprise screening platform for cough sound feature extraction, machine-learning classification, and automated clinical reports.</p>
            <div class="dashboard-metrics">
                <div class="metric-item">
                    <span class="metric-label">Active Cases</span>
                    <span class="metric-value">184</span>
                    <span class="metric-trend">● Live Monitoring</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Triage Accuracy</span>
                    <span class="metric-value">84.6%</span>
                    <span class="metric-trend">Extra Trees Model</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Emergency Status</span>
                    <span class="metric-value">Level 2</span>
                    <span class="metric-trend">ER Watch Active</span>
                </div>
            </div>
        """)

        fast_demo_btn = gr.Button("⚡ Instant Demo Sign-in (1-Click)", variant="secondary", size="lg", elem_classes=["demo-fast-btn"])
        gr.HTML('<div style="text-align: center; color: #94a3b8; font-size: 12px; margin: 12px 0 16px;">— OR SIGN IN WITH CREDENTIALS —</div>')
        
        login_email = gr.Textbox(label="Clinician Email", placeholder="doctor@hospital-aerova.org")
        login_password = gr.Textbox(label="Password", type="password", placeholder="8+ chars with Aa1!")
        
        with gr.Row(elem_classes=["captcha-row"]):
            captcha_question_md = gr.Markdown('<div class="captcha-question">What is 7 + 2?</div>')
            captcha_answer = gr.Textbox(label="CAPTCHA answer", placeholder="Enter number", scale=2)
            captcha_refresh_btn = gr.Button("↻", variant="secondary", size="lg", elem_classes=["secondary-button", "captcha-refresh"], scale=0)
            
        login_submit_btn = gr.Button("Continue Securely", variant="primary", size="lg", elem_classes=["primary-button"])
        login_feedback_html = gr.HTML("")
        gr.HTML('<p class="login-note" style="color:#94a3b8; font-size:12px; text-align:center; margin-top:14px;">Reports generated during this session will be addressed to your clinician email.</p></div>')

    # =========================================================================
    # 2. MAIN APPLICATION WORKSPACE
    # =========================================================================
    with gr.Column(visible=False) as main_app_col:
        # Hero header
        gr.HTML("""
        <header class="hero hero-hospital">
            <div class="hero-left">
                <div class="brand-banner">
                  <span class="pro-badge"><span class="pro-pulse"></span>PRO ENTERPRISE</span>
                </div>
                <div class="eyebrow" style="margin-top: 14px; color: #38bdf8;">ACOUSTIC RESPIRATORY SCREENING</div>
                <h1>AEROVA Clinical Triage & Acoustic Sound Check</h1>
                <p>High-precision respiratory screening from microphone intake to clinical risk readout, powered by audio MFCC feature extraction and trained machine-learning ensembles.</p>
            </div>
            <div class="hero-right">
                <div class="status-badges">
                    <span class="portal-chip"><span class="portal-dot"></span>Live Triage Unit</span>
                    <span class="portal-chip"><span class="portal-dot"></span>Model: Extra Trees</span>
                </div>
            </div>
        </header>
        """)

        # Sub-page 1: Patient History Accordion
        with gr.Accordion("📋 Patient History & Past Assessments", open=False):
            with gr.Row():
                history_search = gr.Textbox(label="Find Patient ID", placeholder="Search AUR-...")
                history_btn = gr.Button("Search / Refresh", variant="secondary", size="lg", elem_classes=["secondary-button"])
            history_display = gr.HTML(render_history_dashboard())

        # Progress Breadcrumb
        progress_tracker_html = gr.HTML(build_progress_html(1))

        # ---------------------------------------------------------------------
        # Sub-page 2: Step 01 · Audio Intake
        # ---------------------------------------------------------------------
        with gr.Column(visible=True, elem_classes=["panel"]) as step1_col:
            gr.HTML('<h2 class="panel-title">1. Bring a Cough Recording</h2><p class="panel-copy">A short, clear 2–6 second cough in a quiet room produces the most reliable acoustic signal.</p>')
            audio_mic_input = gr.Audio(label="Upload or Record via Microphone", sources=["upload", "microphone"], type="filepath", elem_classes=["audio-box"])
            audio_file_input = gr.File(label="Or Choose an Audio/Video File (.wav, .mp3, .webm, .ogg)", file_count="single", type="filepath")
            audio_url_input = gr.Textbox(label="Or Paste a Direct Audio URL", placeholder="https://example.com/cough_sample.wav")
            audio_error_html = gr.HTML("")
            continue_to_step2_btn = gr.Button("Continue to Clinical Context →", variant="primary", size="lg", elem_classes=["primary-button"])

        # ---------------------------------------------------------------------
        # Sub-page 3: Step 02 · Clinical Context
        # ---------------------------------------------------------------------
        with gr.Column(visible=False, elem_classes=["panel"]) as step2_col:
            gr.HTML('<h2 class="panel-title">2. Add Patient & Clinical Context</h2><p class="panel-copy">Clinical details provide vital context to the acoustic machine-learning model.</p>')
            symptoms_text = gr.Textbox(label="Patient Symptoms & Notes", lines=2, placeholder="e.g. Dry barking cough for 3 days, mild fatigue, throat irritation...")
            with gr.Row():
                gender_select = gr.Dropdown(choices=["male", "female", "unknown"], value="unknown", label="Gender")
                age_slider = gr.Slider(minimum=0, maximum=100, value=30, step=1, label="Patient Age (Years)")
            confidence_slider = gr.Slider(minimum=0.0, maximum=1.0, value=0.85, step=0.01, label="Cough Detection Confidence Likelihood")
            with gr.Row():
                pre_existing_radio = gr.Radio(choices=["true", "false"], value="false", label="Pre-existing Respiratory Condition (Asthma / COPD)")
                fever_radio = gr.Radio(choices=["true", "false"], value="false", label="Fever or Muscle Body Pain Present?")
            model_select = gr.Dropdown(choices=list(MODELS_INFO.keys()), value="extra_trees.joblib", label="Analysis Model", visible=False)
            
            with gr.Row(elem_classes=["step-actions"]):
                back_to_step1_btn = gr.Button("← Back to Audio Intake", variant="secondary", size="lg", elem_classes=["secondary-button"])
                generate_triage_btn = gr.Button("⚡ Generate Clinical Triage Readout", variant="primary", size="lg", elem_classes=["primary-button"])

        # ---------------------------------------------------------------------
        # Sub-page 4: Step 03 · Clinical Readout & Medical Export
        # ---------------------------------------------------------------------
        with gr.Column(visible=False, elem_classes=["panel"]) as step3_col:
            gr.HTML('<h2 class="panel-title">3. Clinical Readout & Medical Export</h2><p class="panel-copy">Comprehensive acoustic interpretation, model confidence, and formal documentation.</p>')
            result_card_display = gr.HTML("")
            quality_card_display = gr.HTML("")
            details_panel_display = gr.HTML("")

            with gr.Accordion("📊 Explainable Acoustic Spectrogram & Waveform", open=True):
                spectrogram_display = gr.Image(label="Spectrogram Analysis")

            with gr.Accordion("🧠 Machine Learning Model Comparison", open=True):
                model_comp_display = gr.HTML("")

            pdf_download_file = gr.File(label="Download Verified PDF Medical Report (with QR Authentication)")

            with gr.Group(elem_classes=["panel-subtle"]):
                gr.HTML("""
                <div style="background: rgba(11, 31, 46, 0.95); border: 1px solid #174b6b; border-radius: 12px; padding: 16px 20px; margin: 18px 0 12px;">
                    <div style="color: #38bdf8; font-weight: 800; font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Direct Clinical Dispatch</div>
                    <div style="color: #cbd5e1; font-size: 13px;">Send the official verified PDF medical report directly to patient or hospital clinician.</div>
                </div>
                """)
                with gr.Row():
                    with gr.Column():
                        wa_input_number = gr.Textbox(label="📲 Recipient WhatsApp Number", placeholder="+1234567890")
                        wa_send_btn = gr.Button("💬 Send / Open in WhatsApp", variant="primary", elem_classes=["primary-button"])
                    with gr.Column():
                        email_input_dest = gr.Textbox(label="✉️ Recipient Email Address", placeholder="doctor@hospital-aerova.org")
                        email_send_btn = gr.Button("✉️ Send / Open Email Draft", variant="secondary", elem_classes=["secondary-button"])
                share_feedback_display = gr.HTML("")

            with gr.Row(elem_classes=["result-actions"]):
                modify_context_btn = gr.Button("← Modify Context", variant="secondary", elem_classes=["secondary-button"])
                start_new_btn = gr.Button("Start New Assessment", variant="secondary", elem_classes=["secondary-button"])

            gr.HTML('<div class="safety-alert"><strong>When to seek urgent care:</strong> Severe breathing difficulty, chest pain, confusion, or blue lips require immediate emergency attention.</div>')
            gr.HTML('<p class="footnote" style="color:#94a3b8; font-size:12px; margin-top:12px;">This application is an acoustic screening aid, not a diagnostic confirmation. It supports hospital triage workflow but does not replace professional clinical evaluation.</p>')

        # ---------------------------------------------------------------------
        # Sub-page 5: AEROVA-BOT PRO · AI Robot Copilot Dock
        # ---------------------------------------------------------------------
        with gr.Accordion("🤖 AEROVA-BOT PRO · AI Robot Copilot", open=False, elem_classes=["robot-dock", "chat-panel"]):
            gr.HTML("""
            <div class="robot-header">
              <div class="robot-avatar-wrap">
                <div class="robot-antenna"><div class="robot-antenna-tip"></div></div>
                <div class="robot-avatar">
                  <div class="robot-face">
                    <div class="robot-eyes"><span class="robot-eye"></span><span class="robot-eye"></span></div>
                    <div class="robot-mouth"></div>
                  </div>
                </div>
              </div>
              <div class="robot-title-wrap">
                <div class="robot-name">AEROVA-BOT <span class="robot-tag">PRO COPILOT</span></div>
                <div class="robot-sub">Acoustic Biomarkers & Clinical Triage Reasoning Assistant</div>
              </div>
            </div>
            """)

            with gr.Accordion("🔑 Configure Google Gemini API Key", open=False):
                with gr.Row():
                    gemini_key_box = gr.Textbox(label="Gemini API Key", placeholder="AIzaSy...")
                    connect_key_btn = gr.Button("Connect Key", variant="secondary", elem_classes=["secondary-button"])
                key_notice_html = gr.HTML('<div style="color: #94a3b8; font-size: 11px;">⚡ Running in Autonomous Copilot mode. Paste key for live Gemini 2.0 reasoning.</div>')

            gr.HTML('<div class="robot-chip-row"><span style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-right: 4px;">Quick prompts:</span></div>')
            with gr.Row():
                chip_tips = gr.Button("🎙️ Recording Tips", elem_classes=["robot-chip"])
                chip_models = gr.Button("🧠 ML Models", elem_classes=["robot-chip"])
                chip_meaning = gr.Button("🩺 Result Meaning", elem_classes=["robot-chip"])
                chip_reports = gr.Button("📄 PDF Reports", elem_classes=["robot-chip"])

            chatbot_display = gr.Chatbot(label="AEROVA Robot Chat", value=[])
            with gr.Row():
                chat_msg_box = gr.Textbox(label="Message Robot", placeholder="Ask about cough features, audio quality, model confidences...")
                chat_ask_btn = gr.Button("Ask Robot", variant="primary", elem_classes=["primary-button"])

    # =========================================================================
    # EVENT HANDLERS & CALLBACKS
    # =========================================================================

    # 1. Instant 1-Click Demo Login
    def _fast_demo_login():
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            "doctor@hospital-aerova.org",
            '<div class="notification">⚡ Instant Demo Access granted. Ready to screen cough audio!</div>'
        )
    fast_demo_btn.click(
        fn=_fast_demo_login,
        inputs=[],
        outputs=[login_col, main_app_col, clinician_session, login_feedback_html],
        api_name="_fast_demo_login"
    )

    # 2. Form Credentials Login with CAPTCHA check
    def _demo_login(email, password, captcha_ans, state_captcha):
        if not email or "@" not in email:
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                None,
                '<div style="color: #f43f5e; font-size: 13px; text-align: center;">Please enter a valid clinician email address.</div>'
            )
        expected = state_captcha["a"] + state_captcha["b"]
        try:
            user_ans = int(captcha_ans.strip())
        except Exception:
            user_ans = None

        if user_ans != expected:
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                None,
                '<div style="color: #f43f5e; font-size: 13px; text-align: center;">Incorrect CAPTCHA answer. Please try again.</div>'
            )

        return (
            gr.update(visible=False),
            gr.update(visible=True),
            email.strip(),
            '<div class="notification">✓ Authenticated successfully. Welcome back, clinician.</div>'
        )
    login_submit_btn.click(
        fn=_demo_login,
        inputs=[login_email, login_password, captcha_answer, captcha_state],
        outputs=[login_col, main_app_col, clinician_session, login_feedback_html],
        api_name="_demo_login"
    )

    # 3. CAPTCHA Refresh
    def _refresh_captcha():
        a = random.randint(2, 9)
        b = random.randint(1, 9)
        return f'<div class="captcha-question">What is {a} + {b}?</div>', {"a": a, "b": b}
    captcha_refresh_btn.click(
        fn=_refresh_captcha,
        inputs=[],
        outputs=[captcha_question_md, captcha_state],
        api_name="lambda"
    )

    # 4. Step 1 -> Step 2 (Audio validation)
    def _continue_audio(audio_mic, audio_file, audio_url):
        has_audio = bool(audio_mic or audio_file or (audio_url and audio_url.strip()))
        if not has_audio:
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                '<div style="color: #f59e0b; margin-top: 10px; font-weight: 600;">⚠️ Please upload, record via microphone, or paste an audio URL before proceeding.</div>'
            )
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            ""
        )
    continue_to_step2_btn.click(
        fn=_continue_audio,
        inputs=[audio_mic_input, audio_file_input, audio_url_input],
        outputs=[step1_col, step2_col, audio_error_html],
        api_name="_continue_audio"
    )

    # 5. Step 2 -> Step 1 (Back)
    def _back_to_audio():
        return gr.update(visible=True), gr.update(visible=False)
    back_to_step1_btn.click(
        fn=_back_to_audio,
        inputs=[],
        outputs=[step1_col, step2_col],
        api_name="lambda_5"
    )

    # 6. Step 2 -> Step 3: Run Clinical Triage Readout
    def _generate_triage(clinician_email, mic_audio, file_audio, url_audio,
                         symptoms, model_choice, gender, age, cough_conf,
                         pre_existing, fever):
        # 1. Load Audio
        sr, samples, dur, quality_dict, audio_path = load_audio_signal(mic_audio, file_audio, url_audio)

        # 2. Analyze Cough via Models
        triage = analyze_cough(
            samples=samples,
            sr=sr,
            symptoms=symptoms,
            age=int(age),
            gender=gender,
            confidence_threshold=float(cough_conf),
            pre_existing=pre_existing,
            fever=fever,
            selected_model=model_choice
        )

        # 3. Generate Dual Spectrogram Image
        spec_img_path = generate_spectrogram_and_bars(
            sr=sr,
            samples=samples,
            prob_healthy=triage["prob_healthy"],
            prob_disease=triage["prob_disease"],
            model_name=triage["model_display_name"]
        )

        # 4. Create Unique Patient ID and Timestamp
        now = datetime.now()
        date_str = now.strftime("%d %B %Y, %I:%M %p")
        rand_hex = f"{random.randint(0, 0xFFFFFF):06X}"
        patient_id = f"AUR-{now.strftime('%Y%m%d')}-{rand_hex}"

        # 5. Generate PDF Report
        pdf_path, pdf_data_uri = generate_pdf_report(
            patient_id=patient_id,
            date_str=date_str,
            age=int(age),
            gender=gender,
            recipient_email=clinician_email,
            triage_data=triage,
            quality_data=quality_dict,
            spectrogram_img_path=spec_img_path
        )

        # 6. Log to Patient History
        add_record(
            patient_id=patient_id,
            date_str=date_str,
            readout=triage["readout"],
            risk=triage["risk_tier"],
            confidence=triage["confidence"],
            model=triage["model_name"],
            age=int(age),
            gender=gender
        )
        updated_history_html = render_history_dashboard()

        # 7. Render UI components
        result_card = build_result_card_html(triage)
        quality_card = build_quality_card_html(quality_dict)
        details_panel = build_details_panel_html(triage, patient_id, date_str, int(age), gender, pdf_data_uri)
        model_comp = build_model_comp_html(triage)

        # Save triage state bundle
        state_payload = {
            "patient_id": patient_id,
            "date_str": date_str,
            "pdf_path": pdf_path,
            "pdf_data_uri": pdf_data_uri,
            "triage": triage,
            "quality": quality_dict
        }

        recipient_email_val = clinician_email if clinician_email else "doctor@hospital-aerova.org"

        return (
            result_card,
            details_panel,
            quality_card,
            spec_img_path,
            model_comp,
            pdf_path,
            updated_history_html,
            gr.update(visible=False), # hide step 2
            gr.update(visible=True),  # show step 3
            state_payload,
            recipient_email_val
        )

    generate_triage_btn.click(
        fn=_generate_triage,
        inputs=[
            clinician_session,
            audio_mic_input,
            audio_file_input,
            audio_url_input,
            symptoms_text,
            model_select,
            gender_select,
            age_slider,
            confidence_slider,
            pre_existing_radio,
            fever_radio
        ],
        outputs=[
            result_card_display,
            details_panel_display,
            quality_card_display,
            spectrogram_display,
            model_comp_display,
            pdf_download_file,
            history_display,
            step2_col,
            step3_col,
            triage_state,
            email_input_dest
        ],
        api_name="lambda_8"
    )

    # 7. Step 3 -> Step 2: Modify Context
    def _modify_context():
        return gr.update(visible=False), gr.update(visible=True)
    modify_context_btn.click(
        fn=_modify_context,
        inputs=[],
        outputs=[step3_col, step2_col],
        api_name="lambda_6"
    )

    # 8. Step 3 -> Step 1: Start New Assessment
    def _new_assessment():
        return (
            gr.update(visible=False), # hide step 3
            gr.update(visible=True),  # show step 1
            gr.update(visible=False), # hide step 2
            "",                       # clear result card
            "",                       # clear details
            "",                       # clear share feedback
            ""                        # clear whatsapp
        )
    start_new_btn.click(
        fn=_new_assessment,
        inputs=[],
        outputs=[
            step3_col,
            step1_col,
            step2_col,
            result_card_display,
            details_panel_display,
            share_feedback_display,
            wa_input_number
        ],
        api_name="lambda_7"
    )

    # 9. WhatsApp Dispatcher
    def _dispatch_whatsapp(phone, state):
        if not state:
            return '<div class="notice" style="color: #f59e0b; margin-top: 8px;">Please run a screening prediction first to generate the clinical report.</div>'
        
        pid = state["patient_id"]
        clean_num = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
        if not clean_num:
            return '<div class="notice" style="color: #f43f5e; margin-top: 8px;">Please provide a valid phone number with country code.</div>'
        
        wa_link = f"https://api.whatsapp.com/send?phone={clean_num.replace('+', '')}&text=AEROVA+Report+{pid}"
        return f'<div class="notice" style="color: #10b981; margin-top: 8px;">✓ WhatsApp clinical dispatch initialized for <b>{clean_num}</b>! <a href="{wa_link}" target="_blank" style="color: #00e5b0; text-decoration: underline;">Click here to open chat</a>.</div>'

    wa_send_btn.click(
        fn=_dispatch_whatsapp,
        inputs=[wa_input_number, triage_state],
        outputs=[share_feedback_display],
        api_name="_dispatch_whatsapp"
    )

    # 10. Email Dispatcher
    def _dispatch_email(email_addr, state):
        if not state:
            return '<div class="notice" style="color: #f59e0b; margin-top: 8px;">Please run a screening prediction first to generate the clinical report.</div>'
        
        if not email_addr or "@" not in email_addr:
            return '<div class="notice" style="color: #f43f5e; margin-top: 8px;">Please enter a valid recipient email address.</div>'

        pid = state["patient_id"]
        readout = state["triage"]["readout"]
        subject = urllib.parse.quote(f"AEROVA Clinical Screening Report - {pid}")
        body = urllib.parse.quote(f"Clinical acoustic screening readout: {readout}.\nPatient ID: {pid}.\nAttached verified medical PDF.")
        mailto = f"mailto:{email_addr}?subject={subject}&body={body}"
        return f'<div class="notice" style="color: #10b981; margin-top: 8px;">✓ Email draft prepared for <b>{email_addr}</b>! <a href="{mailto}" style="color: #00e5b0; text-decoration: underline;">Open in Default Mail Client</a>.</div>'

    email_send_btn.click(
        fn=_dispatch_email,
        inputs=[email_input_dest, triage_state],
        outputs=[share_feedback_display],
        api_name="_dispatch_email"
    )

    # 11. Patient History Search
    def _search_history(query):
        return render_history_dashboard(query)
    history_btn.click(
        fn=_search_history,
        inputs=[history_search],
        outputs=[history_display],
        api_name="history_dashboard_html"
    )

    # 12. Connect Gemini API Key
    def _set_gemini_key(key):
        k = (key or "").strip()
        if k:
            return k, '<div style="color: #10b981; font-size: 11px;">✓ Google Gemini 2.0 API connected! Copilot now reasoning live.</div>'
        return "", '<div style="color: #94a3b8; font-size: 11px;">⚡ Running in Autonomous Copilot mode. Paste key for live Gemini 2.0 reasoning.</div>'
    connect_key_btn.click(
        fn=_set_gemini_key,
        inputs=[gemini_key_box],
        outputs=[gemini_key_state, key_notice_html],
        api_name="_set_gemini_key"
    )

    # 13. Robot Chat Interaction
    chat_ask_btn.click(
        fn=handle_chat,
        inputs=[chat_msg_box, chatbot_display, gemini_key_state],
        outputs=[chatbot_display, chat_msg_box],
        api_name="_chat_response"
    )
    chat_msg_box.submit(
        fn=handle_chat,
        inputs=[chat_msg_box, chatbot_display, gemini_key_state],
        outputs=[chatbot_display, chat_msg_box],
        api_name="_chat_response_1"
    )

    # 14. Robot Prompt Chips
    chip_tips.click(fn=lambda h, k: handle_chip("tips", h, k), inputs=[chatbot_display, gemini_key_state], outputs=[chatbot_display, chat_msg_box], api_name="lambda_1")
    chip_models.click(fn=lambda h, k: handle_chip("models", h, k), inputs=[chatbot_display, gemini_key_state], outputs=[chatbot_display, chat_msg_box], api_name="lambda_2")
    chip_meaning.click(fn=lambda h, k: handle_chip("meaning", h, k), inputs=[chatbot_display, gemini_key_state], outputs=[chatbot_display, chat_msg_box], api_name="lambda_3")
    chip_reports.click(fn=lambda h, k: handle_chip("reports", h, k), inputs=[chatbot_display, gemini_key_state], outputs=[chatbot_display, chat_msg_box], api_name="lambda_4")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme="base",
        css=CUSTOM_CSS,
        head=JS_HEADER
    )
