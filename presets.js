/**
 * DDJ-FLX10 向けトランジション辞書（Pattern DB）プリセットデータ
 * フレーズ境界（8小節=32拍）と帯域分離（EQ Mid/High + HPF Filter）を重視した実戦スコア
 */
const SCORE_PRESETS = {
  // 0. SHM 実曲解析データに基づく実践ミックス (Greyhound -> Antidote)
  shm_greyhound_antidote: {
    "routine_name": "SHM Set: Greyhound → Antidote (Phrase Mix)",
    "description": "Greyhound 後半フレーズ（64小節目付近）から8小節聴かせ、フレーズ頭で Antidote をハイパス＋Lowカットで重ね、65拍目にキレのあるBass Swap、その後HPFで美しく抜きます。",
    "bpm": 127.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 0.0, "low": 0.0, "mid": 0.5, "high": 0.7, "filter": 0.25, "drums": true, "vocal": true, "inst": true }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 120.43, "source_bpm": 127.66 },
      { "beat": 33.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 0.043, "source_bpm": 127.0 },
      { "beat": 33.0, "deck": 2, "target": "FADER", "value": 0.85, "action": "ramp", "duration_beats": 16 },
      { "beat": 49.0, "deck": 2, "target": "FILTER", "value": 0.0, "action": "ramp", "duration_beats": 16 },
      { "beat": 64.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "ramp", "duration_beats": 1 },
      { "beat": 65.0, "deck": 2, "target": "EQ_LOW", "value": 1.0, "action": "ramp", "duration_beats": 1 },
      { "beat": 65.0, "deck": 2, "target": "EQ_MID", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 2, "target": "EQ_HIGH", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 2, "target": "FADER", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 1, "target": "EQ_MID", "value": 0.5, "action": "ramp", "duration_beats": 4 },
      { "beat": 73.0, "deck": 1, "target": "FILTER", "value": 0.75, "action": "ramp", "duration_beats": 24 },
      { "beat": 73.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "ramp", "duration_beats": 24 }
    ]
  },

  // 1. STANDARD_BASS_SWAP: 王道24小節クラブミックス（8小節助走 + 16小節ミックス）
  standard_bass_swap: {
    "routine_name": "Club Standard Bass Swap (24Bar Phrase)",
    "description": "Deck 1後半（32小節目）から8小節グルーヴを聴かせ、33拍目のフレーズ頭でDeck 2をLowカット＆Mid抑えめでイン。65拍目で1拍スワップし、HPFスイープで綺麗にアウトします。",
    "bpm": 128.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 0.0, "low": 0.0, "mid": 0.55, "high": 0.75, "filter": 0.2, "drums": true, "vocal": true, "inst": true }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 60.0 },
      { "beat": 33.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 0.0 },
      { "beat": 33.0, "deck": 2, "target": "FADER", "value": 0.85, "action": "ramp", "duration_beats": 16 },
      { "beat": 49.0, "deck": 2, "target": "FILTER", "value": 0.0, "action": "ramp", "duration_beats": 16 },
      { "beat": 64.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "ramp", "duration_beats": 1 },
      { "beat": 65.0, "deck": 2, "target": "EQ_LOW", "value": 1.0, "action": "ramp", "duration_beats": 1 },
      { "beat": 65.0, "deck": 2, "target": "EQ_MID", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 2, "target": "EQ_HIGH", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 2, "target": "FADER", "value": 1.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 65.0, "deck": 1, "target": "EQ_MID", "value": 0.5, "action": "ramp", "duration_beats": 4 },
      { "beat": 73.0, "deck": 1, "target": "FILTER", "value": 0.78, "action": "ramp", "duration_beats": 24 },
      { "beat": 73.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "ramp", "duration_beats": 24 }
    ]
  },

  // 2. STEMS_VOCAL_ECHO_OUT: Track Aのボーカルをエコーで飛ばし、Track Bドロップへ突入
  stems_vocal_echo_out: {
    "routine_name": "Stems Vocal Echo-Out Drop Mix",
    "description": "Deck 1を8小節聴かせた後、17拍目でDrums/Instを抜いてアカペラ化し、HPFとエコーで空間を作って33拍目ジャストにDeck 2のドロップ頭を叩き込みます。",
    "bpm": 128.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 0.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 60.0 },
      { "beat": 17.0, "deck": 1, "target": "STEM_DRUMS", "value": 0.0, "action": "cut" },
      { "beat": 17.0, "deck": 1, "target": "STEM_INST", "value": 0.0, "action": "cut" },
      { "beat": 17.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "ramp", "duration_beats": 4 },
      { "beat": 25.0, "deck": 1, "target": "FILTER", "value": 0.55, "action": "ramp", "duration_beats": 7 },
      { "beat": 32.0, "deck": 1, "target": "BEAT_FX", "value": "ECHO", "action": "cut" },
      { "beat": 33.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 30.0 },
      { "beat": 33.0, "deck": 2, "target": "FADER", "value": 1.0, "action": "cut" }
    ]
  },

  // 3. BUILDUP_FILTER_SWEEP: ビルドアップ部のフィルター上昇＆1拍抜きドロップ解放
  buildup_filter_sweep: {
    "routine_name": "Buildup Filter Sweep & Drop Switch",
    "description": "4小節助走の後、17拍目からDeck 1をHPFスイープで持ち上げつつDeck 2のビルドアップを重ね、ドロップ直前（32拍目）で1拍無音のタメを作って33拍目ジャストに解放します。",
    "bpm": 128.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 0.0, "low": 0.0, "mid": 0.65, "high": 0.8, "filter": 0.2, "drums": true, "vocal": true, "inst": true }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 60.0 },
      { "beat": 17.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 15.0 },
      { "beat": 17.0, "deck": 2, "target": "FADER", "value": 0.8, "action": "ramp", "duration_beats": 12 },
      { "beat": 17.0, "deck": 2, "target": "FILTER", "value": 0.0, "action": "ramp", "duration_beats": 12 },
      { "beat": 17.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "ramp", "duration_beats": 8 },
      { "beat": 17.0, "deck": 1, "target": "FILTER", "value": 0.85, "action": "ramp", "duration_beats": 14 },
      { "beat": 25.0, "deck": 1, "target": "EQ_MID", "value": 0.35, "action": "ramp", "duration_beats": 6 },
      { "beat": 32.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "cut" },
      { "beat": 32.0, "deck": 2, "target": "FADER", "value": 0.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "EQ_LOW", "value": 1.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "EQ_MID", "value": 1.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "EQ_HIGH", "value": 1.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "FADER", "value": 1.0, "action": "cut" }
    ]
  },

  // 4. LOOP_ROLL_CUTIN: ブレイク直前のループロール短縮と即時カットイン
  loop_roll_cutin: {
    "routine_name": "Loop Roll Shorten & Drop Cut-In",
    "description": "Deck 1の後半フレーズを4小節聴かせた後、17拍目から4→2→1→0.5拍とループロールを詰めながらHPFを上げ、25拍目ジャストにDeck 2のドロップ頭を叩き込みます。",
    "bpm": 128.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 60.0 },
      { "beat": 17.0, "deck": 1, "target": "LOOP", "value": 4, "action": "cut" },
      { "beat": 17.0, "deck": 1, "target": "EQ_LOW", "value": 0.2, "action": "ramp", "duration_beats": 6 },
      { "beat": 21.0, "deck": 1, "target": "LOOP", "value": 2, "action": "cut" },
      { "beat": 21.0, "deck": 1, "target": "FILTER", "value": 0.65, "action": "ramp", "duration_beats": 3.5 },
      { "beat": 23.0, "deck": 1, "target": "LOOP", "value": 1, "action": "cut" },
      { "beat": 24.0, "deck": 1, "target": "LOOP", "value": 0.5, "action": "cut" },
      { "beat": 24.5, "deck": 1, "target": "FADER", "value": 0.0, "action": "cut" },
      { "beat": 25.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 30.0 }
    ]
  },

  // 5. STEMS_DRUM_SWAP: 上ネタをキープしたままドラム・ベースパートのみ先行交換
  stems_drum_swap: {
    "routine_name": "Stems Drum & Bass Swap Mix",
    "description": "Deck 1のグルーヴを4小節聴かせた後、17拍目でDeck 1のDrums/Lowを抜きつつDeck 2のDrumsをイン。33拍目でDeck 2の上ネタ・ボーカルを開放して自然に入れ替えます。",
    "bpm": 128.0,
    "initial_state": {
      "deck1": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": true, "inst": true },
      "deck2": { "fader": 1.0, "low": 1.0, "mid": 1.0, "high": 1.0, "filter": 0.0, "drums": true, "vocal": false, "inst": false }
    },
    "sequence": [
      { "beat": 1.0, "deck": 1, "target": "PLAY", "action": "cut", "offset_sec": 60.0 },
      { "beat": 17.0, "deck": 1, "target": "STEM_DRUMS", "value": 0.0, "action": "cut" },
      { "beat": 17.0, "deck": 1, "target": "EQ_LOW", "value": 0.0, "action": "cut" },
      { "beat": 17.0, "deck": 2, "target": "PLAY", "action": "cut", "offset_sec": 0.0 },
      { "beat": 33.0, "deck": 2, "target": "STEM_VOCAL", "value": 1.0, "action": "cut" },
      { "beat": 33.0, "deck": 2, "target": "STEM_INST", "value": 1.0, "action": "cut" },
      { "beat": 33.0, "deck": 1, "target": "FILTER", "value": 0.7, "action": "ramp", "duration_beats": 16 },
      { "beat": 33.0, "deck": 1, "target": "FADER", "value": 0.0, "action": "ramp", "duration_beats": 16 }
    ]
  }
};
