"""
Gemini Live APIクライアント

リアルタイム音声対話を管理（Google Gemini版）
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Any, Dict, List

from google import genai
from google.genai import types

from config import Config
from prompts import get_system_prompt
from capabilities import get_executor

# ロガー設定（main.pyと同じロガーを使用）
logger = logging.getLogger("conversation")


class GeminiRealtimeClient:
    """Gemini Live APIクライアント"""

    def __init__(self, audio_handler, on_response_complete: Optional[Callable] = None):
        self.api_key = Config.get_google_api_key()
        self.audio_handler = audio_handler
        self.on_response_complete = on_response_complete

        self.executor = get_executor()

        # Gemini クライアント初期化
        self.client = genai.Client(api_key=self.api_key)
        self.session = None
        self.is_connected = False
        self.is_responding = False
        self.loop = None

        self.needs_reconnect = False
        self.reconnect_count = 0
        self.needs_session_reset = False
        self.last_response_time = None
        self.last_audio_time = None

        # 音声メッセージモード
        self.voice_message_mode = False
        self.voice_message_timestamp = None

        # 録音状態
        self._is_recording = False

    def _get_session_config(self) -> Dict[str, Any]:
        """セッション設定を取得"""
        return {
            "response_modalities": ["AUDIO"],
            "system_instruction": get_system_prompt(),
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=Config.VOICE
                    )
                )
            ),
            "realtime_input_config": {
                "automatic_activity_detection": {"disabled": True}
            },
            "tools": self.executor.get_gemini_tools(),
        }

    async def connect(self) -> None:
        """接続"""
        try:
            config = self._get_session_config()
            self.session = await self.client.aio.live.connect(
                model=Config.MODEL,
                config=config
            )
            self.is_connected = True
            self.loop = asyncio.get_event_loop()

            logger.info("Gemini Live API接続完了")
        except Exception as e:
            logger.error(f"接続エラー: {e}")
            raise

    async def disconnect(self) -> None:
        """切断"""
        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None
            self.is_connected = False

    async def send_activity_start(self) -> None:
        """音声活動開始を通知"""
        if not self.is_connected or not self.session:
            return

        self._is_recording = True

        try:
            # 手動アクティビティ検出: 録音開始を通知
            await self.session.send_realtime_input(
                activity_start=types.ActivityStart()
            )
        except Exception as e:
            logger.error(f"activity_start送信エラー: {e}")

    async def send_activity_end(self) -> None:
        """音声活動終了を通知（レスポンス生成をトリガー）"""
        if not self.is_connected or not self.session:
            return

        self._is_recording = False

        try:
            # 手動アクティビティ検出: 録音終了を通知
            await self.session.send_realtime_input(
                activity_end=types.ActivityEnd()
            )
        except Exception as e:
            logger.error(f"activity_end送信エラー: {e}")

    async def clear_input_buffer(self) -> None:
        """入力バッファをクリア（Geminiでは特に処理なし）"""
        pass

    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """音声チャンクをリアルタイムで送信"""
        if not self.is_connected or not self.session:
            return

        if self._is_recording:
            try:
                # Gemini Live APIにリアルタイムで音声を送信
                await self.session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_data,
                        mime_type=f"audio/pcm;rate={Config.SEND_SAMPLE_RATE}"
                    )
                )
            except Exception as e:
                logger.error(f"音声送信エラー: {e}")

    async def send_text_message(self, text: str) -> None:
        """テキストメッセージを送信（アラーム通知用）"""
        if not self.is_connected or not self.session:
            return

        try:
            await self.session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=text)]
                ),
                turn_complete=True
            )
        except Exception as e:
            logger.error(f"テキスト送信エラー: {e}")

    async def send_tool_response(self, function_responses: List[types.FunctionResponse]) -> None:
        """ツール実行結果を送信"""
        if not self.is_connected or not self.session:
            return

        try:
            await self.session.send_tool_response(function_responses=function_responses)
        except Exception as e:
            logger.error(f"ツール結果送信エラー: {e}")

    async def receive_messages(self) -> None:
        """メッセージ受信ループ"""
        try:
            while self.is_connected and self.session:
                try:
                    async for response in self.session.receive():
                        await self._handle_response(response)
                        self.reconnect_count = 0
                except Exception as e:
                    if "closed" in str(e).lower():
                        logger.warning("セッションが閉じられました")
                        self.is_connected = False
                        self.needs_reconnect = True
                        break
                    raise

        except Exception as e:
            logger.error(f"受信エラー: {e}")
            self.is_connected = False
            self.needs_reconnect = True

    async def _handle_response(self, response) -> None:
        """レスポンスを処理"""
        # サーバーコンテンツ（音声/テキスト出力）
        if response.server_content:
            self.is_responding = True
            content = response.server_content

            # 音声出力
            if hasattr(content, 'model_turn') and content.model_turn:
                for part in content.model_turn.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_data = part.inline_data.data
                        if audio_data:
                            self.audio_handler.play_audio_chunk(audio_data)
                            self.last_audio_time = time.time()

                    # テキスト（トランスクリプト）
                    if hasattr(part, 'text') and part.text:
                        logger.info(f"[AI] {part.text}")

            # ターン完了
            if hasattr(content, 'turn_complete') and content.turn_complete:
                self.is_responding = False
                self.last_response_time = time.time()
                if self.on_response_complete:
                    self.on_response_complete()

            # 入力音声のトランスクリプト
            if hasattr(content, 'input_transcription') and content.input_transcription:
                logger.info(f"[USER] {content.input_transcription}")

        # ツール呼び出し
        if response.tool_call:
            await self._handle_tool_call(response.tool_call)

        # ツール呼び出しキャンセル
        if response.tool_call_cancellation:
            logger.info("ツール呼び出しがキャンセルされました")

    async def _handle_tool_call(self, tool_call) -> None:
        """ツール呼び出しを処理"""
        function_responses = []

        for fc in tool_call.function_calls:
            name = fc.name
            arguments = dict(fc.args) if fc.args else {}

            logger.info(f"[CAPABILITY] {name} {arguments}")

            # 長時間かかる処理は別スレッドで
            if name in ["voice_send_photo", "camera_capture", "gmail_send_photo"]:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: self.executor.execute(name, arguments)
                )
            else:
                result = self.executor.execute(name, arguments)

            # voice_sendの場合は録音モードを有効化
            if result.data and result.data.get("start_voice_recording"):
                self.voice_message_mode = True
                self.voice_message_timestamp = time.time()

            # FunctionResponseを作成
            function_responses.append(
                types.FunctionResponse(
                    id=fc.id,
                    name=name,
                    response={"result": result.message}
                )
            )

        # ツール結果を送信
        if function_responses:
            await self.send_tool_response(function_responses)

    async def reset_session(self) -> bool:
        """セッションリセット"""
        await self.disconnect()

        if not self.voice_message_mode:
            self.voice_message_mode = False
            self.voice_message_timestamp = None

        try:
            await self.connect()
            return True
        except Exception:
            self.needs_reconnect = True
            return False

    async def reconnect(self) -> bool:
        """再接続（指数バックオフ）"""
        self.reconnect_count += 1
        if self.reconnect_count > Config.MAX_RECONNECT_ATTEMPTS:
            return False

        delay = min(Config.RECONNECT_DELAY_BASE ** self.reconnect_count, 60)
        await asyncio.sleep(delay)

        await self.disconnect()
        self.needs_reconnect = False

        if not self.voice_message_mode:
            self.voice_message_mode = False
            self.voice_message_timestamp = None

        try:
            await self.connect()
            return True
        except Exception:
            self.needs_reconnect = True
            return False

    def check_voice_message_timeout(self) -> bool:
        """音声メッセージモードのタイムアウトチェック"""
        if self.voice_message_mode and self.voice_message_timestamp:
            elapsed = time.time() - self.voice_message_timestamp
            if elapsed > Config.VOICE_MESSAGE_TIMEOUT:
                self.voice_message_mode = False
                self.voice_message_timestamp = None
                return False
        return self.voice_message_mode

    def reset_voice_message_mode(self) -> None:
        """音声メッセージモードをリセット"""
        self.voice_message_mode = False
        self.voice_message_timestamp = None
