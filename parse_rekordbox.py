import xml.etree.ElementTree as ET
import json
import os
import sys
import argparse

def parse_rekordbox_xml(xml_path: str, target_track_ids: list = None, search_query: str = None) -> list:
    """
    rekordbox XMLファイルを読み込み、Track JSONメタデータを抽出する。
    """
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"rekordbox XML file not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    collection = root.find("COLLECTION")
    if collection is None:
        raise ValueError("COLLECTION node not found in the XML file.")

    tracks = []

    for track_elem in collection.findall("TRACK"):
        track_id = track_elem.get("TrackID")
        name = track_elem.get("Name", "Unknown Title")
        artist = track_elem.get("Artist", "Unknown Artist")
        tonality = track_elem.get("Tonality", "")
        avg_bpm_str = track_elem.get("AverageBpm", "0.0")

        try:
            bpm = round(float(avg_bpm_str), 2)
        except ValueError:
            bpm = 0.0

        if target_track_ids and track_id not in target_track_ids:
            continue

        if search_query:
            query_lower = search_query.lower()
            if query_lower not in name.lower() and query_lower not in artist.lower():
                continue

        first_downbeat_sec = 0.0
        tempo_elem = track_elem.find("TEMPO")
        if tempo_elem is not None:
            inizio_str = tempo_elem.get("Inizio", "0.0")
            try:
                first_downbeat_sec = round(float(inizio_str), 3)
            except ValueError:
                first_downbeat_sec = 0.0

        cues = {}
        for idx, mark in enumerate(track_elem.findall("POSITION_MARK")):
            cue_num = mark.get("Num", str(idx + 1))
            cue_name = mark.get("Name") or f"Cue {cue_num}"
            start_sec_str = mark.get("Start", "0.0")
            try:
                start_sec = round(float(start_sec_str), 3)
            except ValueError:
                start_sec = 0.0

            if bpm > 0:
                sec_per_beat = 60.0 / bpm
                elapsed_beats = max(0.0, (start_sec - first_downbeat_sec) / sec_per_beat)
                bar = int(elapsed_beats // 4) + 1
            else:
                bar = 1

            cue_key = f"cue_{cue_num}" if cue_num != "-1" else f"mem_{idx+1}"
            cues[cue_key] = {
                "name": cue_name,
                "bar": bar,
                "time_sec": start_sec
            }

        phrases = []
        for phrase_elem in track_elem.findall("PHRASE"):
            kind = phrase_elem.get("Kind", "")
            start_bar = int(phrase_elem.get("Start", "1"))
            bars = int(phrase_elem.get("Bars", "0"))
            phrases.append({
                "type": kind,
                "start_bar": start_bar,
                "bars": bars
            })

        track_data = {
            "track_id": track_id,
            "title": name,
            "artist": artist,
            "bpm": bpm,
            "key": tonality,
            "first_downbeat_sec": first_downbeat_sec,
            "cues": cues,
            "phrases": phrases
        }
        tracks.append(track_data)

    return tracks

def generate_llm_prompt(track_a: dict, track_b: dict, pattern: str = "STANDARD_BASS_SWAP") -> str:
    """
    2曲のメタデータから、チャットにそのまま貼れるプロンプトテキストを生成する。
    """
    bpm_a = track_a.get("bpm") or 128.0
    downbeat_a = track_a.get("first_downbeat_sec") or 0.0
    bar_sec_a = (60.0 / bpm_a) * 4.0 if bpm_a > 0 else 1.875
    sample_out_bar64 = round(downbeat_a + 64 * bar_sec_a, 3)

    prompt = f"""以下の2曲を使って、Pioneer DJ DDJ-FLX10 向けのプロ品質なトランジション楽譜（DJ Score JSON）を作成してください。

【希望トランジション】
指定パターン: {pattern}
全体構成: 24小節（96拍）推奨（最初の8小節=32拍はTrack Aを単体で聴かせ、33拍目のフレーズ頭から16小節かけて繋ぐ）

【重要：どこから流すか・どこで繋ぐか・どう繋ぐかの音楽的ルール】
1. どこから流すか（Cue / Offset）:
   - Track A を曲の頭（0.0秒）から流さないでください。後半のドロップ終わり〜アウトロ入口にあたる小節頭（例: 64小節目 = {sample_out_bar64}秒 付近、または cues の後半マーカー）から開始してください。
   - Track B は `first_downbeat_sec` またはイントロ/ビルドアップの明確な小節頭 Cue から開始してください。
   - 必ず `source_bpm` を各 PLAY イベントに含めて、2曲のテンポを自動シンクさせてください。
2. どこでつなげるか（Phrase Matching）:
   - すべての展開（Track B イン、Bass Swap、Filter Out）は8小節（32拍）または4小節（16拍）のフレーズ境界（beat: 1, 17, 33, 49, 65, 81, 97）に合わせてください。
3. どうつなげるか（帯域分離 & 質感）:
   - `initial_state.deck2` は `fader: 0.0`, `low: 0.0`, `mid: 0.55`, `high: 0.75`, `filter: 0.2` のように、最初から低域と中域を逃がして待機させてください。
   - `EQ_LOW` が同時に 1.0 で重ならないようにし、Bass Swap は 1〜2拍（`duration_beats: 1` または `2`）でキレよく入れ替え、同時に Track A の `EQ_MID` を `0.5` へ下げて帯域を譲ってください。
   - Track A を抜く終盤は `FILTER`（0.0 → 0.75 の HPF スイープ）と `FADER`（1.0 → 0.0）を同時にかけて自然に空間へ溶かしてください。
   - ボーカルがぶつかる場合は Track A の `STEM_VOCAL: 0.0` を活用してください。

【Track A (Outgoing / Deck 1)】
{json.dumps(track_a, indent=2, ensure_ascii=False)}

【Track B (Incoming / Deck 2)】
{json.dumps(track_b, indent=2, ensure_ascii=False)}

【出力形式】
純粋なJSONオブジェクトのみを出力してください（`routine_name`, `description`, `bpm`, `initial_state`, `sequence` を含むこと）。
"""
    return prompt

def resolve_xml_path(specified_path: str = None) -> str:
    if specified_path:
        return specified_path
    candidates = [
        "rekordbox.xml",
        r"G:\マイドライブ\音楽\rekordbox.xml",
        "sample_rekordbox.xml",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError("rekordbox.xml が見つかりません。パスを指定するか、作業フォルダまたは G:\\マイドライブ\\音楽\\ に配置してください。")

def main():
    parser = argparse.ArgumentParser(description="rekordbox XML Parser for DDJ-FLX10 Score Generator")
    parser.add_argument("xml_file", nargs="?", help="Path to rekordbox.xml (省略時は自動検出)")
    parser.add_argument("--list", action="store_true", help="List TrackID, Title, BPM, Key concisely")
    parser.add_argument("--ids", nargs="+", help="Specific TrackIDs to extract")
    parser.add_argument("--query", help="Keyword search for Track Title or Artist")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    
    # プロンプト一括生成オプション
    parser.add_argument("--deck1", help="TrackID for Deck 1 (Outgoing)")
    parser.add_argument("--deck2", help="TrackID for Deck 2 (Incoming)")
    parser.add_argument("--pattern", default="STANDARD_BASS_SWAP", help="Transition Pattern ID")
    parser.add_argument("--prompt", action="store_true", help="Generate full LLM prompt directly")

    args = parser.parse_args()

    try:
        xml_path = resolve_xml_path(args.xml_file)

        # 一覧表示モード
        if args.list:
            tracks = parse_rekordbox_xml(xml_path, target_track_ids=args.ids, search_query=args.query)
            print(f"XML: {xml_path} ({len(tracks)} tracks)")
            for t in tracks:
                print(f"  ID:{t['track_id']:>5} | {t['bpm']:>6} BPM | {t['key']:>3} | {t['title']} - {t['artist']}")
            return

        # プロンプト生成モード
        if args.prompt and args.deck1 and args.deck2:
            tracks = parse_rekordbox_xml(xml_path, target_track_ids=[args.deck1, args.deck2])
            track_a = next((t for t in tracks if t["track_id"] == args.deck1), None)
            track_b = next((t for t in tracks if t["track_id"] == args.deck2), None)
            
            if not track_a or not track_b:
                print(f"Error: Could not find both Track IDs ({args.deck1}, {args.deck2}) in XML.", file=sys.stderr)
                sys.exit(1)
            
            full_prompt = generate_llm_prompt(track_a, track_b, args.pattern)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(full_prompt)
                print(f"Prompt written to {args.output}")
            else:
                print(full_prompt)
            return

        # 通常のJSON抽出モード
        results = parse_rekordbox_xml(xml_path, target_track_ids=args.ids, search_query=args.query)
        json_output = json.dumps(results, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Extracted {len(results)} tracks to {args.output}")
        else:
            print(json_output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
