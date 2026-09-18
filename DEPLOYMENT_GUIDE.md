# 🌐 AEROVA PRO — Cloud Deployment & Public Access Guide

This guide explains how to make **AEROVA PRO** accessible to anyone in the world over the internet, exactly like `https://cough-audio-demo.onrender.com`.

---

## 📌 Summary of Options

| Method | Public URL Format | Setup Time | Computer Needs to Stay On? | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **1. Render.com** *(Recommended)* | `https://your-app.onrender.com` | ~5 mins | ❌ No (Runs 24/7 in Cloud) | **Exact duplicate of demo link**, production, permanent sharing |
| **2. Gradio `--share`** | `https://xxxx.gradio.live` | 10 seconds | ✔️ Yes (Runs from your PC) | Instant testing with friends or clients |
| **3. Hugging Face Spaces** | `https://huggingface.co/spaces/...` | ~3 mins | ❌ No (Runs 24/7 in Cloud) | AI demo showcases, portfolio |

---

## 🚀 Option 1: Deploy on Render.com (Identical to `cough-audio-demo.onrender.com`)

The website `https://cough-audio-demo.onrender.com` is hosted on **Render.com** (a popular cloud platform that offers free hosting for web apps).

### Step 1: Push Your Code to GitHub

1. If you haven't already, install [Git](https://git-scm.com/) and create a free account on [GitHub](https://github.com/).
2. Create a **New Repository** on GitHub (e.g. `aerova-pro`). Keep it **Public** or **Private**.
3. In your terminal in `d:\Projects\Aerova`, link your repository and push:
   ```powershell
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/aerova-pro.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Create a Free Account on Render

1. Go to **[https://render.com](https://render.com)**.
2. Click **Get Started for Free** and log in with your GitHub account.

### Step 3: Create the Web Service

1. On your Render Dashboard, click the **New +** button (top right) and select **Web Service**.
2. Select **Build and deploy from a Git repository** and click **Next**.
3. Find your `aerova-pro` repository from the list and click **Connect**.
4. Fill in the settings:
   - **Name**: `aerova-pro` (or any unique name you choose; this becomes `https://<name>.onrender.com`)
   - **Region**: Closest to you (e.g., `Singapore`, `Frankfurt`, `Oregon`, `Ohio`)
   - **Branch**: `main` (or `master`)
   - **Runtime**: `Python`
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     python app.py
     ```
   - **Instance Type**: Select **Free** (0.5 CPU, 512 MB RAM)

### Step 4: Add Environment Variables (Optional)

Under the **Environment Variables** section:
- `PYTHON_VERSION`: `3.11.8`
- `GRADIO_SERVER_PORT`: `10000`
- *(Optional)* `GEMINI_API_KEY`: Paste your Google Gemini API key if you want the Copilot robot to have AI reasoning enabled by default for all visitors.

### Step 5: Deploy!

1. Click **Deploy Web Service** at the bottom.
2. Render will automatically:
   - Clone your repository.
   - Install all dependencies from `requirements.txt`.
   - Start `python app.py`.
3. Within 2–3 minutes, you will see `==> Your service is live 🎉` and your public URL at the top left:
   ```
   https://aerova-pro.onrender.com
   ```
4. Anyone in the world on any device or network can now open this link!

---

## ⚡ Option 2: Instant Public Link via Gradio Share (10 Seconds)

If you want to quickly let someone test your app right now without setting up GitHub or cloud accounts:

1. Open PowerShell in `d:\Projects\Aerova`.
2. Run:
   ```powershell
   .\.venv\Scripts\python.exe app.py --share
   ```
3. Gradio creates a secure public tunnel and outputs:
   ```
   * Running on local URL:  http://127.0.0.1:7860
   * Running on public URL: https://a1b2c3d4e5f6.gradio.live
   ```
4. Copy the `https://....gradio.live` link and send it to anyone via WhatsApp, Email, or Slack.
5. They can open it immediately on their mobile phone or laptop, even across cellular 4G/5G or different Wi-Fi networks.
6. *Note*: The link stays active as long as your terminal remains open.

---

## 🤗 Option 3: Deploy on Hugging Face Spaces (Free Alternative)

Gradio is maintained by Hugging Face, which provides dedicated free hosting for Gradio apps:

1. Sign up at **[https://huggingface.co](https://huggingface.co)**.
2. Go to **Spaces** -> **Create New Space** ([huggingface.co/new-space](https://huggingface.co/new-space)).
3. Fill in:
   - **Space name**: `aerova-pro`
   - **Space SDK**: **Gradio**
   - **Hardware**: **CPU basic · 2 vCPU · 16GB RAM · FREE**
4. Clone the space or push your code:
   ```powershell
   git remote add space https://huggingface.co/spaces/<YOUR_USERNAME>/aerova-pro
   git push space main
   ```
5. Hugging Face will automatically build and host the app permanently at:
   `https://huggingface.co/spaces/<YOUR_USERNAME>/aerova-pro`

---

## 🛠️ What We Configured in Your Codebase

We have already configured your project so all the above deployment methods work out of the box:

1. **Dynamic Port Binding** in [app.py](file:///d:/Projects/Aerova/app.py):
   ```python
   port = int(os.environ.get("PORT", os.environ.get("GRADIO_SERVER_PORT", 7860)))
   enable_share = "--share" in sys.argv or os.environ.get("GRADIO_SHARE", "false").lower() in ("true", "1", "yes")
   ```
   Cloud providers (Render, Hugging Face, Railway) assign a dynamic port via `$PORT`. Your app now automatically detects and binds to whatever port the host requests.

2. **Render Blueprint Configuration** in [render.yaml](file:///d:/Projects/Aerova/render.yaml):
   Allows Render to detect build settings automatically if you deploy via Blueprint.

3. **Production Dockerfile** in [Dockerfile](file:///d:/Projects/Aerova/Dockerfile):
   Allows 1-click deployment on container platforms (Google Cloud Run, AWS App Runner, Fly.io).

4. **Optimized Requirements** in [requirements.txt](file:///d:/Projects/Aerova/requirements.txt):
   Pinned dependencies for Python 3.11.
