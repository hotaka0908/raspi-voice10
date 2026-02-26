# AI Necklace v10 - ウェアラブル音声AIアシスタント（Gemini Live API版）

Raspberry Pi 5 + Google Gemini Live API を使用したネックレス型リアルタイム音声AIアシスタント

## 概要

**AI Necklace v10**は、raspi-voice4をベースに機能を大幅に拡張したウェアラブル音声AIアシスタントです。Capability UXアーキテクチャを採用し、モジュール化された能力を組み合わせて様々なタスクを実行します。

### raspi-voice4からの追加機能

| 機能 | 説明 |
|------|------|
| **Googleカレンダー** | 予定の確認・追加・管理 |
| **Web検索** | Tavily APIによるインターネット検索 |
| **ビデオ通話** | WebRTCによるスマホとのビデオ通話 |
| **音楽再生** | YouTubeからの音楽ストリーミング |
| **プロアクティブリマインダー** | 外出予定を検知して自動リマインド |
| **詳細情報送信** | カメラで見たものの詳細をスマホに送信 |
| **メール→カレンダー自動登録** | メール送信時に予定を自動検出・登録 |

## システムアーキテクチャ

```
┌──────────────────┐          WebSocket           ┌──────────────────────┐
│                  │  ◄────────────────────────►  │                      │
│  Raspberry Pi 5  │     Gemini Live API          │   Google Cloud       │
│                  │     (リアルタイム音声)         │                      │
│  ┌────────────┐  │                              │  ┌────────────────┐  │
│  │ マイク     │  │         REST API             │  │ Gemini API     │  │
│  │ スピーカー │  │  ─────────────────────►      │  │ (Vision)       │  │
│  │ カメラ     │  │     画像認識・STT             │  └────────────────┘  │
│  │ GPIOボタン │  │                              │                      │
│  └────────────┘  │         REST API             │  ┌────────────────┐  │
│                  │  ─────────────────────►      │  │ Gmail API      │  │
│  Capabilities    │     メール操作                │  │ Calendar API   │  │
│  (モジュール式)  │                              │  └────────────────┘  │
└──────────────────┘                              │                      │
         │                                        │  ┌────────────────┐  │
         │ Firebase REST API                      │  │ Tavily API     │  │
         │ WebRTC                                 │  │ (Web検索)      │  │
         ▼                                        │  └────────────────┘  │
┌──────────────────────────────────────────────────────────────────────────┐
│                           Firebase                                       │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │ Cloud Storage   │   │ Realtime DB     │   │ Hosting             │    │
│  │ - lifelogs/     │   │ - messages/     │   │ - スマホ用PWA       │    │
│  │ - audio/        │   │ - videocall/    │   │ - ビデオ通話        │    │
│  └─────────────────┘   └─────────────────┘   └─────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
         ▲
         │ Firebase SDK / WebRTC
┌──────────────────┐
│ スマホ (PWA)      │
│ - 音声メッセージ  │
│ - ライフログ確認  │
│ - ビデオ通話     │
└──────────────────┘
```

## 主な機能

| 機能 | 説明 | 使用サービス |
|------|------|-------------|
| リアルタイム音声対話 | 話しかけると即座に応答 | Gemini Live API |
| Gmail連携 | メール確認・返信・送信を音声で操作 | Gmail API |
| Googleカレンダー | 予定の確認・追加・管理 | Calendar API |
| Web検索 | インターネット検索 | Tavily API |
| カメラ | 撮影して「何が見える？」と質問 | Gemini Vision API |
| 詳細情報 | 見たものの詳細をスマホに送信 | Gemini Vision + Firebase |
| ライフログ | 1分間隔で自動撮影、AI分析 | Gemini Vision |
| 音声メッセージ | スマホと音声・写真をやり取り | Firebase |
| ビデオ通話 | スマホとリアルタイムビデオ通話 | WebRTC + Firebase |
| 音楽再生 | YouTube音楽をストリーミング再生 | yt-dlp |
| アラーム | 時刻指定で音声通知 | ローカル処理 |
| プロアクティブリマインダー | 外出予定前に自動リマインド | Calendar + Gemini Vision |

## 必要なもの

### ハードウェア

| パーツ | 用途 |
|-------|------|
| Raspberry Pi 5 | メイン処理 |
| USBマイク | 音声入力 |
| USBスピーカー | 音声出力 |
| Raspberry Pi Camera | 画像撮影 |
| GPIOボタン (GPIO 5) | Push-to-Talk |

### ソフトウェア・API

| 項目 | 必須/任意 |
|------|----------|
| Python 3.11+ | 必須 |
| Google Gemini API キー | 必須 |
| Gmail API 認証情報 | 任意 |
| Google Calendar API | 任意 |
| Tavily API キー | 任意 |
| Firebase プロジェクト | 任意 |

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/hotaka0908/raspi-voice10.git
cd raspi-voice10
```

### 2. Python環境を構築

```bash
sudo apt update
sudo apt install -y ffmpeg portaudio19-dev python3-lgpio

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 環境変数を設定

```bash
mkdir -p ~/.ai-necklace
cat > ~/.ai-necklace/.env << 'EOF'
# 必須
GOOGLE_API_KEY=your-gemini-api-key

# Web検索（任意）
TAVILY_API_KEY=your-tavily-api-key

# プロアクティブリマインダー（任意）
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
HOME_ADDRESS=your-home-address

# Firebase（任意）
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
EOF
```

### 4. 実行

```bash
python main.py
```

### 5. systemdサービスとして実行（オプション）

```bash
sudo cp ai-necklace.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-necklace
sudo systemctl start ai-necklace

# ログ確認
sudo journalctl -u ai-necklace -f
```

## 使い方

ボタンを押しながら話しかけ、離すと応答が返ってきます。

### 基本操作

| 操作 | 動作 |
|------|------|
| ボタン押しながら話す | 音声入力 |
| ボタンを離す | 応答開始 |
| ダブルクリック | セッションリセット |
| 応答後60秒以内にボタン | 音声メッセージモード |

### 音声コマンド例

```
# Gmail
「メールを確認して」
「1番目のメールを読んで」
「返信して、了解しました」

# カレンダー（v10で追加）
「今日の予定は？」
「明日の15時に会議を追加して」
「来週の予定を確認して」

# Web検索（v10で追加）
「最新のニュースを検索して」
「東京の天気を調べて」

# カメラ・ビジョン
「写真を撮って」
「これ何？」
「もっと詳しく」→ 詳細をスマホに送信

# 音声メッセージ
「スマホにメッセージ送って」
「写真をスマホに送って」

# ビデオ通話（v10で追加）
「ビデオ通話して」
「電話して」

# 音楽（v10で追加）
「〇〇の曲をかけて」
「音楽を止めて」

# アラーム
「7時にアラームをセット」
「アラームを確認して」

# ライフログ
「ライフログ開始」
「今日何枚撮った？」
```

## ツール一覧（24種類）

### Gmail（4種類）
| ツール | 説明 |
|--------|------|
| `gmail_list` | メール一覧取得 |
| `gmail_read` | メール本文読み取り |
| `gmail_send` | 新規メール送信 |
| `gmail_reply` | メール返信 |

### カレンダー（3種類）- v10で追加
| ツール | 説明 |
|--------|------|
| `calendar_list` | 予定一覧取得 |
| `calendar_add` | 予定追加 |
| `calendar_delete` | 予定削除 |

### アラーム（3種類）
| ツール | 説明 |
|--------|------|
| `alarm_set` | アラーム設定 |
| `alarm_list` | アラーム一覧取得 |
| `alarm_delete` | アラーム削除 |

### カメラ・ビジョン（4種類）
| ツール | 説明 |
|--------|------|
| `camera_capture` | 撮影して説明 |
| `gmail_send_photo` | 写真付きメール送信 |
| `voice_send_photo` | 写真をスマホに送信 |
| `send_detail_info` | 詳細情報をスマホに送信（v10で追加）|

### 音声メッセージ（2種類）
| ツール | 説明 |
|--------|------|
| `voice_send` | 音声メッセージ送信 |
| `voice_send_photo` | 写真をスマホに送信 |

### ビデオ通話（2種類）- v10で追加
| ツール | 説明 |
|--------|------|
| `videocall_start` | ビデオ通話開始 |
| `videocall_end` | ビデオ通話終了 |

### 音楽（2種類）- v10で追加
| ツール | 説明 |
|--------|------|
| `music_play` | 音楽再生 |
| `music_stop` | 音楽停止 |

### Web検索（1種類）- v10で追加
| ツール | 説明 |
|--------|------|
| `web_search` | Web検索 |

### ライフログ（3種類）
| ツール | 説明 |
|--------|------|
| `lifelog_start` | ライフログ開始 |
| `lifelog_stop` | ライフログ停止 |
| `lifelog_status` | ステータス確認 |

## 技術仕様

### Gemini Live API

| 項目 | 値 |
|------|-----|
| モデル | `gemini-2.5-flash-native-audio-preview-12-2025` |
| 音声 | Aoede（デフォルト） |
| アクティビティ検出 | 手動（ボタン制御） |
| セッション時間 | 最大15分 |

### オーディオ設定

| 項目 | 値 |
|------|-----|
| マイク入力 | 48kHz, 16bit, モノラル |
| Gemini API送信 | 16kHz, 16bit PCM |
| Gemini API受信 | 24kHz, 16bit PCM |
| スピーカー出力 | 48kHz, 16bit, モノラル |

## ディレクトリ構成

```
raspi-voice10/
├── main.py                     # エントリーポイント
├── config.py                   # 設定
├── core/                       # コア機能
│   ├── audio.py                # 音声入出力
│   ├── gemini_realtime_client.py  # Gemini Live APIクライアント
│   ├── firebase_voice.py       # Firebase連携
│   └── videocall.py            # WebRTCビデオ通話
├── capabilities/               # 能力モジュール（Capability UX）
│   ├── base.py                 # 基底クラス
│   ├── executor.py             # 実行エンジン
│   ├── communication.py        # Gmail連携
│   ├── calendar.py             # カレンダー連携
│   ├── schedule.py             # アラーム/リマインダー
│   ├── search.py               # Web検索（Tavily）
│   ├── memory.py               # 記憶/ライフログ
│   ├── vision.py               # ビジョン機能
│   ├── detail_info.py          # 詳細情報送信
│   ├── music.py                # 音楽再生
│   ├── videocall.py            # ビデオ通話
│   └── proactive_reminder.py   # プロアクティブリマインダー
├── prompts/                    # システムプロンプト
└── docs/                       # スマホ用PWA
```

## Gmail/カレンダー認証（オプション）

Gmail・カレンダー機能を使用する場合：

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクト作成
2. Gmail API、Calendar APIを有効化
3. OAuth 2.0クライアントIDを作成（デスクトップアプリ）
4. 認証情報をダウンロード

```bash
cp ~/Downloads/credentials.json ~/.ai-necklace/credentials.json
```

初回起動時にブラウザでOAuth認証が必要です。

## トラブルシューティング

### モデルエラー

Gemini Live APIのモデル名は定期的に更新されます。エラーが発生した場合は、[公式ドキュメント](https://ai.google.dev/gemini-api/docs/models)で最新のモデル名を確認し、`config.py`の`MODEL`を更新してください。

### 接続エラー

```
接続エラー: ...
```

- `GOOGLE_API_KEY`が正しく設定されているか確認
- ネットワーク接続を確認

### マイクが見つからない

```bash
arecord -l  # デバイス一覧を確認
```

### スピーカーから音が出ない

```bash
aplay -l    # デバイス一覧を確認
```

## ライセンス

MIT License

## リンク

- [raspi-voice4（ベース版）](https://github.com/hotaka0908/raspi-voice4)
- [Gemini Live API ドキュメント](https://ai.google.dev/gemini-api/docs/live)
- [Firebase ドキュメント](https://firebase.google.com/docs)
