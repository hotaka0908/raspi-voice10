# raspi-voice10

Raspberry Pi上で動作するCapability UXベースの音声AIアシスタント。**Gemini Live API版**

ユーザーの意図を理解し、適切な能力を選択・組み合わせ、世界を代行して実行する「翻訳層」として機能します。

## raspi-voice7との違い

| 項目 | raspi-voice7 | raspi-voice10 |
|------|--------------|---------------|
| 音声AI | OpenAI Realtime API | Gemini Live API |
| LLM | GPT-4o | Gemini 2.5 Flash |
| STT | Whisper | Gemini内蔵 |
| TTS | OpenAI内蔵 | Gemini内蔵 |
| Vision | GPT-4o Vision | Gemini Vision |
| Search | Tavily API | Tavily API |
| 接続方式 | WebSocket直接 | google-genai SDK |

## 技術仕様

### Gemini Live API
- **モデル**: `gemini-2.5-flash-native-audio-preview-12-2025`
- **入力音声**: 16kHz, 16-bit PCM, モノラル
- **出力音声**: 24kHz, 16-bit PCM
- **アクティビティ検出**: 手動（ボタン制御）

### 音声処理フロー
```
マイク(48kHz) → リサンプリング(16kHz) → Gemini Live API → リサンプリング(48kHz) → スピーカー
```

## 機能

### コア機能
- **リアルタイム音声対話**: Gemini Live APIを使用した自然な音声会話
- **物理ボタン操作**: GPIOボタンで会話開始/終了を制御
- **ダブルクリック**: セッションリセット

### Capabilities（能力）
- **Gmail**: メールの確認・送信・返信
- **Googleカレンダー**: 予定の確認・追加・管理
- **アラーム/リマインダー**: 時間指定の通知
- **Web検索**: インターネット検索（Tavily API）
- **ビジョン**: カメラで見て理解（Gemini Vision）
- **ライフログ**: 日常の記録
- **音声メッセージ**: スマホとの音声メッセージ送受信
- **ビデオ通話**: WebRTCによるスマホとのビデオ通話
- **音楽再生**: YouTube音楽再生

### Voice Messenger
Firebase経由でスマホと連携する音声メッセージ機能。Webアプリ（`docs/`）から音声メッセージの送受信が可能。

## 必要なもの

### ハードウェア
- Raspberry Pi（4以降推奨）
- USBマイク/スピーカー
- 物理ボタン（GPIO5に接続）
- カメラ（オプション: ビジョン機能用）

### ソフトウェア
- Python 3.11+
- ffmpeg
- PortAudio

## セットアップ

### 1. 依存関係のインストール

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv ffmpeg portaudio19-dev python3-lgpio

cd raspi-voice10
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定

`~/.ai-necklace/.env` に以下を設定:

```bash
# 必須: Google API（Gemini Live API、Vision用）
GOOGLE_API_KEY=your_google_api_key

# 任意: Tavily API（Web検索用）
TAVILY_API_KEY=your_tavily_api_key

# 任意: Google Maps API（移動時間計算用）
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# 任意: 自宅住所（プロアクティブリマインダー用）
HOME_ADDRESS=your_home_address
```

### 3. Gmail/カレンダー連携（オプション）

Google Cloud Consoleでプロジェクトを作成し、OAuth認証情報を取得:

```
~/.ai-necklace/credentials.json
```

### 4. Firebase連携（オプション）

Voice Messenger機能を使用する場合:

1. Firebase Consoleでプロジェクトを作成
2. Realtime DatabaseとStorageを有効化
3. サービスアカウントキーを取得して配置:
   ```
   ~/.ai-necklace/firebase-service-account.json
   ```

4. Voice Messenger Webアプリの設定:
   ```bash
   cd docs
   cp firebase-config.example.js firebase-config.js
   # firebase-config.js を編集してFirebaseプロジェクトの設定を入力
   ```

## 実行

```bash
source venv/bin/activate
python main.py
```

### systemdサービスとして実行

```bash
sudo cp ai-necklace.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-necklace
sudo systemctl start ai-necklace
```

## ディレクトリ構成

```
raspi-voice10/
├── main.py                    # エントリーポイント
├── config.py                  # 設定
├── core/                      # コア機能
│   ├── audio.py               # 音声入出力
│   ├── gemini_realtime_client.py  # Gemini Live APIクライアント
│   ├── firebase_voice.py      # Firebase音声メッセージ
│   └── videocall.py           # WebRTCビデオ通話
├── capabilities/              # 能力モジュール
│   ├── communication.py       # Gmail連携
│   ├── calendar.py            # カレンダー連携
│   ├── schedule.py            # アラーム/リマインダー
│   ├── search.py              # Web検索（Tavily）
│   ├── memory.py              # 記憶/ライフログ
│   ├── vision.py              # ビジョン機能（Gemini）
│   ├── music.py               # 音楽再生
│   ├── videocall.py           # ビデオ通話
│   └── proactive_reminder.py  # プロアクティブリマインダー
├── prompts/                   # システムプロンプト
└── docs/                      # Voice Messenger Webアプリ
```

## 使い方

1. ボタンを押しながら話しかける
2. ボタンを離すと応答が開始
3. ダブルクリックでセッションリセット
4. 応答後60秒以内にボタンを押すと音声メッセージモード（スマホに送信）

## 音声設定

Geminiの音声は以下から選択可能（config.pyで設定）:
- Puck
- Charon
- Kore
- Fenrir
- Aoede（デフォルト）

## トラブルシューティング

### モデルエラーが発生する場合
Gemini Live APIのモデル名は定期的に更新されます。エラーが発生した場合は、[公式ドキュメント](https://ai.google.dev/gemini-api/docs/models)で最新のモデル名を確認し、`config.py`の`MODEL`を更新してください。

### 音声が認識されない場合
- マイクが正しく接続されているか確認
- `alsamixer`で入力レベルを確認
- ログで音声チャンクが送信されているか確認

## License

MIT
