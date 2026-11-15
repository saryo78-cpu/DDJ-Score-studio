AIコーディングエージェント（Claude Code、Cursor、Windsurfなど）にそのまま食わせて一発で実装まで走らせることを前提とした、**「洋楽和訳・BPM同期リリック動画生成エンジン」の設計書**です。

---

# 🎵 System Spec: Beat-Synced Lyric Video Generator (Remotion + TS)

## 1. システム概要 & 目的

* **ゴール**: 音源ファイル（MP3/WAV）と歌詞データ（JSON）を入力とし、BPM・ビート位置に完全同期した和訳リリック動画（MP4）を自動レンダリング・出力する。
* **技術スタック**:
* **Core Engine**: Remotion (React 19, TypeScript)
* **Styling**: Tailwind CSS / Lucide-react (必要に応じて)
* **Audio Pre-processing (CLI / Script)**: Python (`librosa` または `aubio` でBPM・ビート配列抽出)
* **Format**: 1080x1920 (縦型 9:16) または 1920x1080 (横型 16:9) 切り替え対応 / 60fps



---

## 2. アーキテクチャ & データ設計

### 2.1 データと描画ロジックの完全分離

エージェントがコードを壊さずに曲ごとの調整を行えるよう、全パラメータはJSONから注入する。

```typescript
// types/schema.ts

export type VisualStyle = 'minimal' | 'cyberpunk' | 'warm';

export interface BeatMap {
  bpm: number;
  first_beat_offset_sec: number;
  beat_timestamps: number[]; // 各ビートの秒数 [0.46, 0.93, 1.40, ...]
}

export interface LyricLine {
  id: string;
  start_sec: number;
  end_sec: number;
  en: string;
  ja: string;
  offset_ms?: number;         // 歌い出しのタメ・突っ込み補正用（ミリ秒）
  accent?: boolean;          // ドロップやキック強調用フラグ
  custom_scale?: number;     // 特定行のみのフォントサイズ倍率
}

export interface SongProject {
  meta: {
    title: string;
    artist: string;
    duration_sec: number;
    fps: number;
  };
  audio_path: string;        // public/ 以下の相対パス
  background: {
    type: 'image' | 'video' | 'gradient';
    src?: string;
    blur_px?: number;
    dim_opacity?: number;     // 背景の暗さ (0.0 - 1.0)
  };
  beats: BeatMap;
  lyrics: LyricLine[];
}

```

---

## 3. ディレクトリ構造

```text
lyric-video-engine/
├── package.json
├── remotion.config.ts
├── tailwind.config.js
├── scripts/
│   └── extract_beats.py         # 音源からBPM・ビート配列を抽出してJSONを吐く補助スクリプト
├── public/
│   ├── audio/                   # 音源ファイル
│   └── assets/                  # 背景画像・ジャケット・動画素材
└── src/
    ├── index.ts                 # Remotion Root
    ├── Root.tsx                 # Composition登録
    ├── types/
    │   └── schema.ts
    ├── data/
    │   └── current_song.json    # レンダリング対象のプロジェクトデータ
    ├── components/
    │   ├── Background.tsx       # 背景ブラー/動画/オーバーレイ描画
    │   ├── LyricOverlay.tsx     # 英語歌詞 + 和訳の配置コンテナ
    │   ├── AnimatedText.tsx     # ビート連動スプリング/タイポグラフィ
    │   └── BeatPulse.tsx        # ビート瞬間の画面微小スケール/グロー制御
    └── hooks/
        └── useBeatSync.ts       # 現在フレームとビート配列の照合フック

```

---

## 4. コアロジック仕様

### 4.1 ビート同期フック (`useBeatSync.ts`)

* **機能**: 現在フレーム（`useCurrentFrame()`）を秒数に変換し、直近のビートとの距離（Delta）を計算。
* **出力**:
* `isBeat`: ビートの瞬間（±1フレーム以内）に `true`
* `beatProgress`: 直近ビートから次ビートまでの正規化進捗値（0.0 〜 1.0）
* `pulseScale`: Remotionの `spring()` を使い、ビート瞬間に 1.05 へ弾けて減衰するスプリング値



### 4.2 テキスト描画コンポーネント (`LyricOverlay.tsx`)

* **レイアウト要件**:
* 画面中央やや下（Vertical Align: 65% 付近）に配置。
* **上段（英語）**: フォントサイズ大（32〜40px）、ウェイト Bold、字間トラッキング広め、ビートに同期して微小なバウンス（`scale`）。
* **下段（和訳）**: フォントサイズ中（22〜26px）、ウェイト Medium、白色＋視認性確保のためのドロップシャドウ（`drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]`）。


* **トランジション**:
* 各行の `start_sec + (offset_ms / 1000)` でフェードイン＋Y軸下からのスライドアップ（3〜5フレーム）。
* 行終了（`end_sec`）でフェードアウト（2フレーム）。



---

## 5. 実装プロンプト（エージェント投入用テンプレート）

バイブコーディング開始時に、AIエージェントへ渡す初期プロンプトです。

```markdown
以下のシステム仕様に基づき、Remotion (TypeScript + React 19 + Tailwind CSS) で
「洋楽和訳・BPM同期リリック動画生成プロジェクト」を新規構築してください。

【開発要件】
1. `types/schema.ts` に定義した `SongProject` 型に基づき、JSONファイルから全データを動的に読み込んで描画する構成にすること。
2. 背景コンポーネント:
   - 静止画ブラー＋ダークオーバーレイで文字の可読性を極限まで高めること。
3. リリック同期コンポーネント:
   - 上段に英語、下段に和訳を表示。
   - `useBeatSync` フックを実装し、ビート配列（beats.beat_timestamps）に合わせて英語テキストが心地よくバウンス（springアニメーション）すること。
   - 歌い出しのタメ・突っ込みに対応するため、各行の `offset_ms` を加味して表示時間を計算すること。
4. サンプルデータ:
   - ダミー音源と、EDM調（BPM 128、4小節分の歌詞データ）の `current_song.json` を含めること。
5. プレビュー & ビルド:
   - `npm run dev` で Remotion Player が立ち上がり、スペースキーで再生・確認できるようにすること。

```

---

## 6. 今後の拡張ロードマップ（フェーズ2）

* **Word-by-word ハイライト**: 文字単位（カラオケ風）のタイムスタンプ同期。
* **オーディオビジュアライザー**: `remotion/media-utils` の `getAudioData()` を使ったスペクトラム波形の描画。
* **Whisper CLI 連携**: 音源からタイムコード付き歌詞SRTを自動生成し、JSONへ変換する自動化スクリプトの追加。

この設計書構成で進める場合、まずはプロジェクトの基盤構築（Remotion初期化とスキーマ/サンプルJSONの作成）からコードを出力できます。