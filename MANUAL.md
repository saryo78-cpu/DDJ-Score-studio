# DDJ-FLX10 楽譜作成・シミュレーションシステム 使用方法マニュアル

本システムは、**楽曲準備 → AIによるDJ楽譜（Score JSON）生成 → ブラウザ試聴 → DDJ-FLX10実機練習（Live HUD）** までをローカル環境で完結させるためのツールです。

---

## 1. クイックスタート（起動方法）

1. ターミナル（PowerShell等）で作業フォルダへ移動し、ローカルサーバーを起動します。
   ```bash
   python server.py
   ```
2. ブラウザで以下のURLを開きます。
   👉 **http://localhost:8000/index.html**

> **Note**: `index.html` を直接開くだけでもプレビュー再生・HUD練習は可能ですが、YouTubeダウンロード機能とCrate（プレイリスト）連携を使う場合は `server.py` の起動が必要です。

---

## 2. 画面構成と基本操作

### ① ヘッダー（上部バー）
* **準備チェック（Standby）**: 曲の再生を始める前に、DDJ-FLX10本体のフェーダー・EQ・Stemsをどの位置にしておくべきかを表示します。
* **Focus HUD（集中モード）**: 右側のパネルを隠し、Deck状態とLive HUDだけを大きく表示します。実機練習時に便利です。
* **JP / EN**: 画面表記を日本語モード／英語モードに切り替えます。
* **マニュアル**: いつでもこの操作ガイドを画面内に表示します。

### ② 右パネル：Track Crate（楽曲ボックス）
* **YouTubeダウンロード**: URLを貼り付けて「DL」を押すと、`downloads/` フォルダに音声を保存し、下のプレイリストに自動追加されます。
* **デッキ装填**: リスト内の **`D1`**（Deck 1: 再生中の曲）／**`D2`**（Deck 2: 次の曲）ボタンを押すと即座に読み込まれます。PC内のWAV/MP3を直接ドラッグ＆ドロップすることも可能です。

### ③ 右パネル：Score & Presets（楽譜JSON・プリセット）
* **プリセット選択**: 5つの定番トランジション（Bass Swap、Vocal Echo-Out、Filter Sweep、Loop Roll Cut-in、Drum Swap）をワンクリックで読み込めます。
* **JSONエディタ**: AIが生成した楽譜JSONをここに貼り付けて「再生」を押すと、Web Audio APIによる自動ミックス試聴が始まります。

### ④ 左パネル：Deck 1 / 2 & Live Practice HUD
* **リアルタイムメーター**: 楽譜のオートメーションに合わせて、FADER / LOW / MID / HIGH のバーと Stems（DRUMS / VOCAL / INST）のON/MUTEが連動します。
* **大型拍カウンター（Bar.Beat）**: 現在の小節と拍を大きく表示します。
* **次の操作（Next Action）**: 次に操作すべき項目と残り拍数をカウントダウン表示します。**4拍以内になると枠が点滅してタイミングを知らせます。**

---

## 3. 楽譜（DJ Score JSON）の作成フロー

1. **rekordboxからXMLをエクスポート**
   * rekordboxのメニュー「ファイル」→「コレクションをXML形式でエクスポート」を実行します。
2. **楽曲メタデータ＆プロンプトの生成**
   * 以下のコマンドで2曲のTrack IDを指定すると、チャットAIに貼り付けるだけの完成形プロンプトが出力されます。
   ```bash
   python parse_rekordbox.py your_rekordbox.xml --deck1 101 --deck2 102 --prompt
   ```
   *(テスト用サンプルを試す場合: `python parse_rekordbox.py sample_rekordbox.xml --deck1 101 --deck2 102 --prompt`)*
3. **LLMで楽譜JSONを生成**
   * [llm_score_prompt_template.md](llm_score_prompt_template.md) のシステムプロンプトを設定したAIチャットに、手順2で出力されたプロンプトを貼り付けます。
4. **試聴＆実機練習**
   * 生成されたJSONをWebプレイヤーの「楽譜・プリセット」タブに貼り付けて再生し、耳で確認した後にLive HUDを見ながらDDJ-FLX10で手動練習します。

---

## 4. トラブルシューティング

* **音が出ない / 曲を読み込めない**:
  * 初回はブラウザの自動再生制限を解除するため、必ず「再生」ボタンを押すか楽曲をロードしてください。
* **YouTubeダウンロードが失敗する**:
  * `server.py` が起動しているか確認してください。また、`yt-dlp` の更新が必要な場合は `pip install -U yt-dlp` を実行してください。
* **Web MIDIが認識されない**:
  * Chrome / Edge などの Web MIDI API 対応ブラウザを使用し、DDJ-FLX10をUSB接続した状態で「DDJ-FLX10接続 (Web MIDI)」を押してください。
