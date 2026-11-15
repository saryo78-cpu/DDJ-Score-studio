# DDJ-FLX10 向け DJ楽譜作成・シミュレーションシステム 設計書

---

## 1. システム概要

### 1.1 背景と目的

DJプレイにおけるトランジション（繋ぎ）は、EQ、フェーダー、ループ、エフェクト、Stems分離などの複数パラメーターを拍単位で制御する高度なリアルタイム操作である。

本システムは、DJプレイの操作手順をタイムライン形式の「楽譜（JSON）」としてコード化し、AIによる自動生成、ブラウザ上での事前プレビュー試聴、そして本番機材（Pioneer DJ DDJ-FLX10）での手動再現を支援するナビゲーション（HUD）を一気通貫で提供することを目的とする。

### 1.2 コアコンセプト

* **完全ノーコード・ローカル完結運用**: 外部有料APIコールを排除し、LLM推論は対話チャット、試聴およびHUDは単一HTMLファイル（Web Audio API）で完結させる。
* **高精度な楽曲骨格解析**: ビートグリッドや小節解析はゼロから自作せず、rekordboxの解析データ（XML）を活用してミリ秒精度の安定性を担保する。
* **FLX10特化のパラメーター体系**: 通常の3バンドEQ・縦フェーダーに加え、FLX10のコア機能である「Stemsミュート」「Part Select FX」をネイティブにサポートする。

---

## 2. 全体アーキテクチャ

```
[ rekordbox ]
      │ (Export Collection)
      ▼
 1. rekordbox.xml ──► [ Parser Script (Python) ]
                               │
                               ▼ (Track JSON)
                      [ チャットUI (LLM) ] ◄── [ トランジション辞書 (Pattern DB) ]
                               │
                               ▼ (Score JSON)
               [ ローカルWebプレイヤー (HTML / Web Audio API) ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
     【Preview Engine】                    【Live Practice HUD】
   ・Web Audioによる自動再生              ・拍/小節リアルタイムカウンター
   ・EQ / Fader / FX 自動制御             ・次操作のカウントダウン表示
   ・耳での事前確認                        ・FLX10手動操作のガイド

```

---

## 3. データ仕様

### 3.1 楽曲メタデータ形式（rekordbox XML パース後）

LLMへ入力するための楽曲情報フォーマット。

```json
{
  "track_id": "101",
  "title": "Sample Track A",
  "artist": "Artist A",
  "bpm": 128.0,
  "key": "8A",
  "first_downbeat_sec": 0.05,
  "cues": {
    "cue_1": { "name": "Intro", "bar": 1, "time_sec": 0.05 },
    "cue_2": { "name": "Drop 1", "bar": 17, "time_sec": 30.05 }
  },
  "phrases": [
    { "type": "Intro", "start_bar": 1, "bars": 16 },
    { "type": "Outro", "start_bar": 81, "bars": 16 }
  ]
}

```

### 3.2 楽譜データ形式（DJ Score JSON）

本システムの中核となる命令フォーマット。時間は楽曲開始からの通算拍数（`beat`）で管理する。

#### パラメーター定義

* `beat` (float / int): 発火タイミング（1小節1拍目 = 1.0、2小節1拍目 = 5.0）。
* `deck` (int): 対象デッキ番号（`1` または `2`）。
* `target` (string): 制御対象
* `PLAY`: 再生トリガー
* `FADER`: チャンネル縦フェーダー（`0.0` 〜 `1.0`）
* `EQ_LOW` / `EQ_MID` / `EQ_HIGH`: 3バンドEQ（`0.0` = -inf/カット、`1.0` = 0dB）
* `STEM_DRUMS` / `STEM_VOCAL` / `STEM_INST`: パートミュート（`true` / `false`）
* `BEAT_FX`: エフェクト制御（`ECHO`, `REVERB`, `ROLL` 等）
* `LOOP`: ループ長（`4`, `8`, `16` 等）


* `action` (string):
* `cut`: 指定値への瞬時切り替え
* `ramp`: 一定拍数をかけた直線変化


* `duration_beats` (float / int): `ramp` 動作時に遷移にかける拍数。

#### スキーマ例

```json
{
  "routine_name": "Standard Bass Swap 16Bar",
  "bpm": 128.0,
  "sequence": [
    { "beat": 1.0, "deck": 2, "target": "PLAY", "action": "cut" },
    { "beat": 1.0, "deck": 2, "target": "EQ_LOW", "value": 0.0, "action": "cut" },
    { "beat": 1.0, "deck": 2, "target": "FADER", "value": 0.8, "action": "ramp", "duration_beats": 16 },
    { "beat": 29.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "ramp", "duration_beats": 4 },
    { "beat": 33.0, "deck": 2, "target": "EQ_LOW", "value": 1.0, "action": "ramp", "duration_beats": 2 },
    { "beat": 49.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "ramp", "duration_beats": 16 }
  ]
}

```

---

## 4. トランジション辞書（Pattern DB）仕様

LLMが選定基準とする定石テンプレート定義。

| パターンID | 適用条件 | 主な動作シーケンス |
| --- | --- | --- |
| **`STANDARD_BASS_SWAP`** | イントロ/アウトロが重なるロングミックス（同キーまたは隣接キー） | 1. Deck 2をLowカット状態で16拍フェードイン<br>

<br>2. 32拍目（8小節末）でDeck 1のLowを急激にカット<br>

<br>3. 33拍目頭でDeck 2のLowを開放（キック入替）<br>

<br>4. 残り16拍でDeck 1をフェードアウト |
| **`STEMS_VOCAL_ECHO_OUT`** | Track Aに明瞭なボーカルがあり、Track Bがドロップから入る展開 | 1. ドロップ16拍前にTrack AのDrums/Instを瞬時ミュート<br>

<br>2. ドロップ1拍前にTrack A VocalにEcho 1/2拍を発火<br>

<br>3. ドロップ頭でTrack Aを即座にキル、Track Bをフルゲイン投入 |
| **`BUILDUP_FILTER_SWEEP`** | ビルドアップ部でテンションを引き上げるミックス | 1. Track Aのハイパスフィルター（HPF）を徐々に持ち上げる<br>

<br>2. Track Bのフェーダーを追従させて上昇<br>

<br>3. ドロップ頭でTrack Aキル、Track Bフィルター解放 |
| **`LOOP_ROLL_CUTIN`** | ブレイク直前で急激にカットインする展開 | 1. Track Aの末尾で4拍➔2拍➔1拍➔半拍とループをロール短縮<br>

<br>2. 最終拍でミュートし、Track Bの頭拍を叩く |
| **`STEMS_DRUM_SWAP`** | Track Aの上ネタを活かしたままリズム隊だけ先に入れ替える | 1. Track AのDrumsのみをミュート<br>

<br>2. 同時にTrack BのDrumsをフルボリュームで導入<br>

<br>3. 8〜16小節後に上ネタ・ボーカルも完全移行 |

---

## 5. Webプレイヤー＆HUD 実装仕様

単一ファイル（HTML5 / JavaScript）で完結するフロントエンド設計。

### 5.1 オーディオグラフ設計（Web Audio API）

各デッキに対して以下のノードチェーンを構成する。

```
[AudioBufferSourceNode] 
      │
      ▼
[BiquadFilterNode (LowShelf: 300Hz)] ── (EQ Low)
      │
      ▼
[BiquadFilterNode (Peaking: 1000Hz)] ── (EQ Mid)
      │
      ▼
[BiquadFilterNode (HighShelf: 4000Hz)] ── (EQ High)
      │
      ▼
[GainNode (Fader)] ── (縦フェーダー)
      │
      ├──────────────────────────────┐
      ▼ (Dry)                        ▼ (Wet - Send)
[Master Destination]           [DelayNode / ConvolverNode] ── (Beat FX)
                                     │
                                     ▼
                               [Master Destination]

```

### 5.2 オートメーション処理

* `AudioParam.setValueAtTime`: `cut` 命令のミリ秒スケジューリングに適用。
* `AudioParam.linearRampToValueAtTime`: `ramp` 命令の補間処理に適用。

### 5.3 Live HUD表示ロジック

* `AudioContext.currentTime` を基準に経過拍数（Beat）・小節位置（Bar.Beat）を50msインターバルで算出。
* **現在のアクション**: `currentBeat` に合致する操作をハイライト表示。
* **カウントダウン表示**: `upcomingBeat - currentBeat` を計算し、「あと N 拍で [CH1] EQ_LOW CUT」といった先読み指示を画面上に提示。

---

## 6. 運用フロー

1. **解析データ準備**:
* rekordboxで楽曲を解析し、XMLをエクスポート。
* Pythonスクリプトで対象2曲のJSONを生成。


2. **チャットでの楽譜生成**:
* 生成された2曲のメタデータを本チャットに貼り付け。
* 「パターン2（ボーカルエコーアウト）で繋いで」等の指示を出し、楽譜JSONを取得。


3. **プレビュー試聴（Web）**:
* ローカルの `index.html` に2曲の音源をD&Dし、楽譜JSONを貼り付けて再生。
* 帯域衝突や不自然な音量変化がないか耳で確認。必要に応じてチャット側でパラメータを微修正。


4. **実機練習（HUD）**:
* 試聴でOKが出た楽譜をもとにHUDモードを起動。
* 画面のカウントダウン表示に沿ってDDJ-FLX10の物理フェーダー・ノブ・パッドを手動操作。



---

## 7. 実装ロードマップ・手順

本システムは動作確認を確実に行いながら進められるよう、以下の順序で段階的に実装を進める。

`
[Phase 1] コアエンジン構築（Webプレイヤー & HUD 単一HTML）
    ├─ 1-1. Web Audio 再生・フェーダー・EQ・エフェクトグラフの構築
    ├─ 1-2. 楽譜JSONのシーケンサー（拍・時間スケジューリング）
    └─ 1-3. リアルタイムHUD表示（小節・拍カウンター、次操作カウントダウン）
          ▼
[Phase 2] テスト用楽譜データ & 検証
    ├─ 2-1. サンプルScore JSON（代表パターン）の作成・プリセット化
    └─ 2-2. 2曲の音源を読み込んでの動作検証（カット/ランプ、フェーダー、EQ動作確認）
          ▼
[Phase 3] rekordbox XML パーサー実装（Python）
    ├─ 3-1. XMLからTrack情報（BPM、BeatGrid、Cue、Phrase）を抽出
    └─ 3-2. LLM入力用メタデータJSONの出力スクリプト作成
          ▼
[Phase 4] LLM向けプロンプト＆トランジション生成フローの整備
    └─ トランジション辞書を組み込んだLLM用プロンプトテンプレート作成
`

---

## 8. 今後の拡張ロードマップ（Phase 2以降）

* **Web MIDI API連携**:
* ブラウザとDDJ-FLX10をUSB接続し、HUDの指示と連動して実機コントローラーのLED（CueボタンやStemsボタン）を点滅させるアシスト機能。


* **Stem事前分離データの統合**:
* プレビュープレイヤー側でDemucs等による事前分離WAV（Vocal/Drums/Inst）のマルチトラック読み込みに対応し、実機以上の高品位なパート抜き差しプレビューを実現。


* **Web Audio タイムストレッチの導入**:
* `SoundTouchJS` などのライブラリを組み込み、異なるBPM間のミックスにおけるキーロック（マスターテンポ）対応。