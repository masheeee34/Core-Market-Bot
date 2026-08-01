import os
import sys
import subprocess

def install_yt_dlp():
    """Installe automatiquement yt-dlp si necessaire."""
    try:
        import yt_dlp
    except ImportError:
        print("[+] Installation de la bibliotheque de telechargement (yt-dlp)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])

def download_twitch_clip(url: str, output_folder: str = "clips"):
    """Telecharge un clip Twitch au format MP4 haute qualite."""
    install_yt_dlp()
    import yt_dlp

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"\n[+] Telechargement du clip Twitch : {url} ...")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"\n[OK] Clip telecharge avec succes dans le dossier : '{os.path.abspath(output_folder)}' !")
    except Exception as e:
        print(f"\n[ERR] Erreur lors du telechargement : {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        clip_url = sys.argv[1]
    else:
        clip_url = input("Entrez l'URL du clip Twitch : ").strip()

    if clip_url:
        download_twitch_clip(clip_url)
    else:
        print("[!] Aucune URL fournie.")
