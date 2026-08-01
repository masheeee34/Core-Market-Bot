import os
import sys
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

def ensure_yt_dlp():
    try:
        import yt_dlp
    except ImportError:
        print("[+] Installation de yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])

ensure_yt_dlp()
import yt_dlp

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Core Market • Bulk Clip Downloader</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0c10;
            --bg-card: rgba(18, 22, 31, 0.85);
            --accent-blue: #0070FF;
            --accent-cyan: #00d2ff;
            --text-primary: #f0f4f8;
            --text-secondary: #94a3b8;
            --border: rgba(255, 255, 255, 0.08);
            --success: #10b981;
            --error: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem 1rem;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 112, 255, 0.15) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(0, 210, 255, 0.1) 0%, transparent 45%);
        }

        .container {
            width: 100%;
            max-width: 680px;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 2.5rem;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(0, 112, 255, 0.1);
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .logo-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 112, 255, 0.12);
            border: 1px solid rgba(0, 112, 255, 0.3);
            color: var(--accent-cyan);
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 1px;
            padding: 6px 14px;
            border-radius: 100px;
            margin-bottom: 12px;
            text-transform: uppercase;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .input-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        textarea {
            width: 100%;
            height: 160px;
            background: rgba(10, 12, 16, 0.7);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem;
            color: var(--text-primary);
            font-family: 'Inter', monospace;
            font-size: 0.9rem;
            resize: vertical;
            transition: all 0.2s ease;
            outline: none;
        }

        textarea:focus {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(0, 112, 255, 0.2);
        }

        textarea::placeholder {
            color: rgba(148, 163, 184, 0.5);
        }

        .btn-download {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 16px;
            background: linear-gradient(135deg, var(--accent-blue) 0%, #0045e6 100%);
            color: white;
            font-family: 'Outfit', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 8px 25px rgba(0, 112, 255, 0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-download:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(0, 112, 255, 0.5);
        }

        .btn-download:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .status-section {
            margin-top: 2rem;
            display: none;
        }

        .status-header {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.05rem;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .results-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 250px;
            overflow-y: auto;
        }

        .result-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            font-size: 0.85rem;
        }

        .result-url {
            color: var(--text-secondary);
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            max-width: 380px;
        }

        .badge {
            padding: 4px 10px;
            border-radius: 100px;
            font-weight: 600;
            font-size: 0.75rem;
        }

        .badge-pending { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-error { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .folder-hint {
            margin-top: 1.5rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .folder-hint code {
            color: var(--accent-cyan);
            background: rgba(0, 210, 255, 0.1);
            padding: 2px 8px;
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-badge">⚡ Core Market Tool</div>
            <h1>Bulk Clip Downloader</h1>
            <p class="subtitle">Collez vos liens de clips Twitch ou YouTube (un par ligne) et téléchargez tout automatiquement dans votre dossier !</p>
        </div>

        <div class="input-group">
            <label for="urls">Liens des Clips (1 lien par ligne)</label>
            <textarea id="urls" placeholder="https://clips.twitch.tv/ExempleClip1&#10;https://www.youtube.com/watch?v=Exemple2&#10;https://www.youtube.com/shorts/Exemple3"></textarea>
        </div>

        <button id="btn-submit" class="btn-download" onclick="startDownload()">
            <span>🚀 Télécharger tous les clips</span>
        </button>

        <div id="status-section" class="status-section">
            <div class="status-header">
                <span>Progression des Téléchargements</span>
                <span id="progress-count" style="color: var(--accent-cyan);">0 / 0</span>
            </div>
            <div id="results-list" class="results-list"></div>
        </div>

        <div class="folder-hint">
            📍 Tous vos fichiers MP4 seront enregistrés dans : <code id="out-folder">...</code>
        </div>
    </div>

    <script>
        document.getElementById('out-folder').innerText = 'c:\\Users\\ayman\\Downloads\\Core-Market-Bot\\clips';

        async function startDownload() {
            const textarea = document.getElementById('urls');
            const rawText = textarea.value.trim();
            if (!rawText) {
                alert("Veuillez coller au moins un lien de clip !");
                return;
            }

            const urls = rawText.split('\\n').map(u => u.trim()).filter(u => u.length > 0);
            if (urls.length === 0) return;

            const btn = document.getElementById('btn-submit');
            btn.disabled = true;
            btn.innerHTML = `<div class="spinner"></div> Téléchargement en cours...`;

            const statusSection = document.getElementById('status-section');
            const resultsList = document.getElementById('results-list');
            const progressCount = document.getElementById('progress-count');

            statusSection.style.display = 'block';
            resultsList.innerHTML = '';
            progressCount.innerText = `0 / ${urls.length}`;

            // Initialize UI list
            urls.forEach((url, idx) => {
                const card = document.createElement('div');
                card.className = 'result-card';
                card.id = `card-${idx}`;
                card.innerHTML = `
                    <span class="result-url">${url}</span>
                    <span class="badge badge-pending" id="badge-${idx}">⏳ En attente...</span>
                `;
                resultsList.appendChild(card);
            });

            let completed = 0;

            for (let i = 0; i < urls.length; i++) {
                const url = urls[i];
                const badge = document.getElementById(`badge-${i}`);
                badge.className = 'badge badge-pending';
                badge.innerText = '🔄 Téléchargement...';

                try {
                    const res = await fetch('/api/download', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await res.json();

                    if (data.status === 'ok') {
                        badge.className = 'badge badge-success';
                        badge.innerText = `✅ ${data.title || 'Téléchargé'}`;
                    } else {
                        badge.className = 'badge badge-error';
                        badge.innerText = `❌ ${data.error || 'Erreur'}`;
                    }
                } catch (err) {
                    badge.className = 'badge badge-error';
                    badge.innerText = '❌ Erreur réseau';
                }

                completed++;
                progressCount.innerText = `${completed} / ${urls.length}`;
            }

            btn.disabled = false;
            btn.innerHTML = `<span>🚀 Télécharger tous les clips</span>`;
            textarea.value = '';
        }
    </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return  # Suppress default HTTP logs for clean output

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/download":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                url = data.get("url", "")
                
                if not url:
                    res = {"status": "error", "error": "URL manquante"}
                else:
                    res = self.download_single_url(url)
            except Exception as e:
                res = {"status": "error", "error": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

    def download_single_url(self, url: str) -> dict:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(OUTPUT_DIR, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Clip MP4')
                return {"status": "ok", "title": title[:30]}
        except Exception as e:
            err_msg = str(e)
            if "no longer available" in err_msg.lower():
                err_msg = "Clip introuvable / supprimé"
            elif "video unavailable" in err_msg.lower():
                err_msg = "Vidéo indisponible"
            else:
                err_msg = err_msg[:35]
            return {"status": "error", "error": err_msg}

def start_server(port=5000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"\n========================================================")
    print(f"[+] Core Market Downloader est LANCE !")
    print(f"[+] Web App accessible sur : http://localhost:{port}")
    print(f"[+] Vos clips iront dans : {OUTPUT_DIR}")
    print(f"========================================================\n")
    
    # Auto open in web browser
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Arret de l'application...")

if __name__ == "__main__":
    start_server(5000)
