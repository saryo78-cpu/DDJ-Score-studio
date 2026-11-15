import os
import re
import sys
import argparse
import yt_dlp

DEFAULT_DOWNLOAD_DIR = r"G:\マイドライブ\音楽\_inbox"

def format_track_basename(info: dict) -> str:
    """YouTubeメタデータから 'Artist - Title' 形式の判別しやすいファイル名を生成する"""
    raw_title = (info.get('track') or info.get('title') or 'Unknown Track').strip()
    artist = (info.get('artist') or info.get('uploader') or '').strip()
    artist = re.sub(r'\s*-\s*Topic$', '', artist, flags=re.IGNORECASE).strip()

    if ' - ' in raw_title or not artist:
        name = raw_title
    else:
        name = f"{artist} - {raw_title}"

    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def download_youtube_audio(url: str, output_dir: str = DEFAULT_DOWNLOAD_DIR, audio_format: str = "mp3") -> str:
    """
    YouTube URLから音声を抽出し、指定フォルダにMP3（または他オーディオ）として保存する。
    ffmpegがシステムにない場合でも、最高音質のネイティブオーディオ（m4a/webm/mp3）を確実に保存。
    """
    os.makedirs(output_dir, exist_ok=True)

    # 先にメタデータを取得して 'Artist - Title' を確定
    with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl_meta:
        meta_info = ydl_meta.extract_info(url, download=False)
    clean_stem = format_track_basename(meta_info)

    # ffmpegの存在有無をチェック
    has_ffmpeg = False
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        has_ffmpeg = (result.returncode == 0)
    except Exception:
        has_ffmpeg = False

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'{clean_stem}.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
    }

    if has_ffmpeg and audio_format.lower() == 'mp3':
        # ffmpegがある場合は320kbps MP3へトランスコード
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]
    else:
        # ffmpegがない場合、mp3に直接トランスコードできないため最高音質オーディオ（m4a/webm等）をそのまま保存
        # （ブラウザのWeb Audio APIはm4a/aac/webm/mp3のいずれも完全対応）
        if not has_ffmpeg and audio_format.lower() == 'mp3':
            print("\n[NOTE] FFmpeg is not installed on your system.")
            print("[NOTE] Saving directly as best native audio format (e.g. M4A/AAC), which is natively supported by rekordbox & Web Audio API.")

    print(f"\n[INFO] Starting download from: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # 拡張子の補正
        if has_ffmpeg and audio_format.lower() == 'mp3':
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"

    print(f"\n[SUCCESS] Download completed!")
    print(f"[FILE] {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description="YouTube Audio Downloader for DJ Practice")
    parser.add_argument("url", nargs="?", help="YouTube video or audio URL")
    parser.add_argument("-o", "--output", default=DEFAULT_DOWNLOAD_DIR, help=f"Output directory (default: {DEFAULT_DOWNLOAD_DIR})")
    parser.add_argument("-f", "--format", default="mp3", help="Audio format (default: mp3)")

    args = parser.parse_args()

    url = args.url
    if not url:
        url = input("Enter YouTube URL: ").strip()

    if not url:
        print("Error: No URL provided.")
        sys.exit(1)

    try:
        download_youtube_audio(url, output_dir=args.output, audio_format=args.format)
    except Exception as e:
        print(f"\n[ERROR] Failed to download: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

