import os
import re

SYSTEM_PROMPT = """You are AEROVA-BOT PRO, the enterprise AI respiratory triage and acoustic copilot assistant for the AEROVA hospital respiratory triage platform.
You assist clinicians and patients with:
1. Cough recording best practices (microphone distance, duration 2-6s, quiet room, avoiding clipping).
2. Acoustic feature extraction (MFCCs, spectral centroid, roll-off, zero-crossing rate, STFT spectrogram).
3. Machine learning models (Extra Trees, Random Forest, AdaBoost, Bagging, Gradient Boosting, Logistic Regression, KNN, Decision Tree, SGD, SVC).
4. Screening readouts: Healthy vs Disease signals, model confidence, clinical risk tiers (Low, Medium, High).
5. Document exports (QR-authenticated PDF medical summary, WhatsApp sharing, EML draft).
6. Clinical safety: Always remind users that this is an acoustic screening aid, not a diagnostic confirmation, and severe breathing difficulties require immediate emergency care.
Maintain a professional, knowledgeable, reassuring, and concise medical copilot tone."""

CHIP_RESPONSES = {
    "tips": (
        "What are the best tips for recording a clear cough?",
        "🎙️ **Recording Best Practices:**\n"
        "- Sit in a quiet room with minimal ambient echo.\n"
        "- Hold your microphone 10–20 cm from your mouth.\n"
        "- Produce 1 to 3 clear, intentional coughs over 2 to 6 seconds.\n"
        "- Avoid touching the microphone or blowing directly into it to prevent acoustic clipping."
    ),
    "models": (
        "Which machine learning models does AEROVA use and how accurate are they?",
        "🧠 **Machine Learning Architecture:**\n"
        "AEROVA evaluates multiple scikit-learn models: Extra Trees Classifier, Random Forest, Logistic Regression, "
        "Support Vector Classifier (SVC), and KNN. The system automatically loads the highest-performing validated "
        "model (Extra Trees / Random Forest) to produce the primary triage readout."
    ),
    "meaning": (
        "What does a Healthy versus Disease result mean in AEROVA?",
        "📊 **Screening Results:**\n"
        "AEROVA analyzes cough audio with trained machine learning models. **Healthy** indicates acoustic patterns "
        "consistent with normal respiration. **Disease** signals an abnormal respiratory acoustic profile requiring "
        "clinical follow-up. Neither result is a final diagnosis."
    ),
    "reports": (
        "How do I export and download a clinical PDF report with QR verification?",
        "📑 **Reports & Exports:**\n"
        "Following screening, AEROVA automatically prepares:\n"
        "- A downloadable **PDF Medical Summary** complete with an authentication QR code.\n"
        "- An **EML email draft** formatted with clinical styling.\n"
        "- An **HTML report** and logged entry in the Patient History Dashboard."
    )
}

def generate_autonomous_response(user_message):
    msg = (user_message or "").strip().lower()
    
    if not msg:
        return "🤖 **Hello! I am AEROVA-BOT PRO**, your respiratory acoustic and clinical AI assistant. How can I help you today? You can ask about recording your cough, audio features, ML models, screening results, or reports."

    if any(k in msg for k in ["hello", "hi", "hey", "who are you", "what can you do"]):
        return "🤖 **Hello! I am AEROVA-BOT PRO**, your respiratory acoustic and clinical AI assistant. How can I help you today? You can ask about recording your cough, audio features, ML models, screening results, or reports."

    if any(k in msg for k in ["tip", "record", "mic", "quiet", "how to"]):
        return CHIP_RESPONSES["tips"][1]

    if any(k in msg for k in ["model", "algorithm", "extra trees", "accuracy", "classifier"]):
        return CHIP_RESPONSES["models"][1]

    if any(k in msg for k in ["result", "mean", "healthy", "disease", "urgent", "risk", "triage"]):
        return CHIP_RESPONSES["meaning"][1]

    if any(k in msg for k in ["pdf", "report", "download", "qr", "whatsapp", "email", "export"]):
        return CHIP_RESPONSES["reports"][1]

    if any(k in msg for k in ["mfcc", "spectrogram", "frequency", "audio"]):
        return (
            "📈 **Acoustic Signal Processing:**\n"
            "AEROVA computes Short-Time Fourier Transforms (STFT) to render frequency spectrograms from 0 to 4000 Hz. "
            "It extracts Mel-Frequency Cepstral Coefficients (MFCCs), spectral centroid, and signal energy (dBFS) "
            "to differentiate between dry spasmodic, wheezing, and normal respiratory acoustic signatures."
        )

    if any(k in msg for k in ["emergency", "severe", "pain", "breath", "doctor", "hospital"]):
        return (
            "⚠️ **Urgent Medical Notice:**\n"
            "If the patient experiences severe breathing difficulty, chest pain, cyanosis (blue lips/skin), or sudden confusion, "
            "please contact emergency medical services or visit the nearest emergency department immediately. "
            "AEROVA is an acoustic triage tool and does not replace emergency clinical evaluation."
        )

    return (
        f"🤖 **Clinical Copilot Response:**\n"
        f"Regarding your query on *\"{user_message.strip()}\"*, AEROVA utilizes non-invasive acoustic biomarkers and patient clinical context "
        f"(age, symptoms, pre-existing conditions) to support hospital respiratory triage. "
        f"You can upload a 2–6 second cough audio sample in Step 01, configure clinical indicators in Step 02, and view the automated readout with export options in Step 03."
    )

def handle_chat(message, history, gemini_api_key=""):
    if history is None:
        history = []

    user_text = message.strip() if message else ""
    if not user_text:
        return history, ""

    bot_reply = ""
    api_key = (gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip()

    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{SYSTEM_PROMPT}\n\nUser: {user_text}\nAssistant:"
            )
            bot_reply = response.text
        except Exception as e:
            bot_reply = f"*(Gemini live response unavailable: {e})*\n\n" + generate_autonomous_response(user_text)
    else:
        bot_reply = generate_autonomous_response(user_text)

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": bot_reply})
    return history, ""

def handle_chip(chip_key, history, gemini_api_key=""):
    if history is None:
        history = []
    
    question, answer = CHIP_RESPONSES.get(chip_key, ("Question", "Answer"))
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    return history, ""
