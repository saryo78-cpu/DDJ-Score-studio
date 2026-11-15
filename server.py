import http.server
import socketserver
import json
import os
import sys
import mimetypes
import urllib.parse
import re
import yt_dlp
from parse_rekordbox import parse_rekordbox_xml, resolve_xml_path, generate_llm_prompt

PORT = 8000
DOWNLOAD_DIR = r"G:\マイドライブ\音楽"
INBOX_DIR = os.path.join(DOWNLOAD_DIR, "_inbox")

try:
    os.makedirs(INBOX_DIR, exist_ok=True)
except Exception as e:
    print(f"[WARN] Could not access or create INBOX_DIR ({INBOX_DIR}): {e}", file=sys.stderr)

def format_track_basename(info: dict) -> str:
    """YouTubeメタデータから 'Artist - Title' 形式の判別しやすいファイル名を生成する"""
    raw_title = (info.get('track') or info.get('title') or 'Unknown Track').strip()
    artist = (info.get('artist') or info.get('uploader') or '').strip()
    # 不要な ' - Topic' 等を除去
    artist = re.sub(r'\s*-\s*Topic$', '', artist, flags=re.IGNORECASE).strip()

    if ' - ' in raw_title or not artist:
        name = raw_title
    else:
        name = f"{artist} - {raw_title}"

    # Windowsファイル名禁止文字を置換
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

class DJAppHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORSヘッダー付与
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # API: rekordbox.xml のトラック一覧取得
        if parsed.path == '/api/xml-tracks':
            try:
                xml_path = resolve_xml_path()
                tracks = parse_rekordbox_xml(xml_path)
                # BPM > 0 のトラックを優先表示しやすいよう整形して返す
                payload = {"success": True, "xml_path": xml_path, "tracks": tracks}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        # API: ダウンロード済み楽曲プレイリストの取得 (G:\マイドライブ\音楽 配下を再帰検索)
        if parsed.path == '/api/playlist':
            files = []
            try:
                if os.path.exists(DOWNLOAD_DIR):
                    for root_dir, _, filenames in os.walk(DOWNLOAD_DIR):
                        for f in filenames:
                            if f.lower().endswith(('.mp3', '.m4a', '.wav', '.webm', '.aac', '.flac', '.ogg')):
                                full_path = os.path.join(root_dir, f)
                                rel_path = os.path.relpath(full_path, DOWNLOAD_DIR).replace('\\', '/')
                                files.append({
                                    "name": rel_path,
                                    "url": f"/downloads/{urllib.parse.quote(rel_path)}",
                                    "size_mb": round(os.path.getsize(full_path) / (1024 * 1024), 2)
                                })
                    files.sort(key=lambda x: x["name"].lower())
            except Exception as e:
                print(f"[SERVER ERROR] Failed to list playlist: {e}", file=sys.stderr)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(files, ensure_ascii=False).encode('utf-8'))
            return

        # ダウンロードフォルダ (G:\マイドライブ\音楽) からの音声ファイル配信
        if parsed.path.startswith('/downloads/'):
            rel_name = urllib.parse.unquote(parsed.path[len('/downloads/'):])
            # ディレクトリトラバーサル防止
            norm_rel = os.path.normpath(rel_name).lstrip('\\/')
            file_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, norm_rel))
            base_dir = os.path.abspath(DOWNLOAD_DIR)
            if not file_path.startswith(base_dir):
                self.send_response(403)
                self.end_headers()
                return

            if os.path.isfile(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                file_size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                try:
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
            else:
                self.send_response(404)
                self.end_headers()
            return

        # 通常の静的ファイル配信
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # API: YouTubeダウンロード
        if parsed.path == '/api/download':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)

            try:
                data = json.loads(post_body.decode('utf-8'))
                url = data.get('url', '').strip()

                if not url:
                    raise ValueError("URL is required")

                os.makedirs(INBOX_DIR, exist_ok=True)
                print(f"\n[SERVER] Received YouTube download request: {url}")

                # まずメタデータ取得して 'Artist - Title' を確定
                with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl_meta:
                    meta_info = ydl_meta.extract_info(url, download=False)
                clean_stem = format_track_basename(meta_info)

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(INBOX_DIR, f'{clean_stem}.%(ext)s'),
                    'noplaylist': True,
                    'quiet': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    base_name = os.path.basename(filename)

                rel_url_path = f"_inbox/{base_name}"
                response_data = {
                    "success": True,
                    "title": clean_stem,
                    "filename": base_name,
                    "file_url": f"/downloads/{urllib.parse.quote(rel_url_path)}"
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                print(f"[SERVER] Download finished: {os.path.join(INBOX_DIR, base_name)}")

            except Exception as e:
                print(f"[SERVER ERROR] {e}", file=sys.stderr)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # API: XMLから2曲を選んでAI用プロンプトを生成
        if parsed.path == '/api/xml-prompt':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            try:
                data = json.loads(post_body.decode('utf-8'))
                d1_id = str(data.get('deck1_id', '')).strip()
                d2_id = str(data.get('deck2_id', '')).strip()
                pattern = data.get('pattern', 'STANDARD_BASS_SWAP')

                xml_path = resolve_xml_path()
                tracks = parse_rekordbox_xml(xml_path, target_track_ids=[d1_id, d2_id])
                track_a = next((t for t in tracks if t["track_id"] == d1_id), None)
                track_b = next((t for t in tracks if t["track_id"] == d2_id), None)
                if not track_a or not track_b:
                    raise ValueError(f"Track ID not found in XML: {d1_id}, {d2_id}")

                prompt_text = generate_llm_prompt(track_a, track_b, pattern)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "prompt": prompt_text}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with ThreadedHTTPServer(("", PORT), DJAppHandler) as httpd:
        print(f"\n========================================================")
        print(f"DDJ-FLX10 App & YouTube Hub Server running at:")
        print(f"-> http://localhost:{PORT}/index.html")
        print(f"Download / Crate Dir: {DOWNLOAD_DIR}")
        print(f"========================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == '__main__':
    run_server()
