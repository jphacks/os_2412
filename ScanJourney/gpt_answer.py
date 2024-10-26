import os
from openai import OpenAI
from datetime import datetime
import base64
from PIL import Image
import io
from gtts import gTTS

class ChatGPTAssistant:
    def __init__(self, openai_api_key):
        """OpenAI APIクライアントの初期化"""
        self.client = OpenAI(api_key=openai_api_key)
        self.conversation_history = []
        
    def encode_image_to_base64(self, image_path):
        """画像をbase64エンコードする"""
        try:
            with Image.open(image_path) as img:
                # 画像サイズが大きい場合はリサイズ
                max_size = 2048
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # 画像をJPEGフォーマットでバイト列に変換
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()

                return base64.b64encode(img_byte_arr).decode('utf-8')
        except Exception as e:
            print(f"画像の処理中にエラーが発生しました: {str(e)}")
            return None

    def process_chat(self, user_input):
        """チャットメッセージを処理する"""
        try:
            messages = self.conversation_history.copy()
            
            # 画像パスが含まれているか確認（例：「画像：path/to/image.jpg」の形式）
            if user_input.startswith('画像：'):
                # 画像パスと質問テキストを分離
                parts = user_input.split('\n', 1)
                image_path = parts[0][3:].strip()  # '画像：' の後のパス
                question = parts[1] if len(parts) > 1 else "また、この画像についても説明してください。"
                
                # 画像をエンコード
                image_data = self.encode_image_to_base64(image_path)
                if image_data:
                    user_message = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                else:
                    return "画像の処理に失敗しました。テキストのみで質問を続けてください。"
            else:
                # テキストのみのメッセージ
                user_message = {
                    "role": "user",
                    "content": [{"type": "text", "text": user_input}]
                }

            messages.append(user_message)

            
            # GPT-4による応答の生成
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500
            )

            # 応答を取得
            assistant_response = response.choices[0].message.content

            # 会話履歴を更新
            self.conversation_history.append(user_message)
            self.conversation_history.append({
                "role": "assistant",
                "content": [{"type": "text", "text": assistant_response}]
            })

            return assistant_response

        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def generate_audio_response(self, text, model, voice, output_dir="audio_output"):
        """応答テキストを音声に変換する"""
        try:
            # 出力ディレクトリが存在しない場合は作成
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # ファイル名に現在時刻を含める
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = os.path.join(output_dir, f"response_{timestamp}.wav")

            if model == "gpt-4o-mini":
              # テキストを音声に変換
              tts = gTTS(text=text, lang='ja', slow=False)
              tts.save(audio_file)
              
            else:
              # GPT-4V-Audio-Previewによる音声生成
              audio_response = self.client.audio.speech.create(
                  model="tts-1",  # TTSモデルを使用
                  voice=voice,   # 音声の種類
                  input=text  # 生成したテキスト
              )
              # 音声を保存
              audio_response.stream_to_file(audio_file)

            return audio_file

        except Exception as e:
            return f"音声生成でエラーが発生しました: {str(e)}"

    def clear_conversation(self):
        """会話履歴をクリアする"""
        self.conversation_history = []


# OpenAI APIキーを設定
openai_api_key = os.getenv("OPENAI_API_KEY")
model = "gpt-4o-mini"
# model = "gpt-4o-audio-preview"
# voice = "alloy"
voice = "nova"

generate_flag = False
generate_audio = input("音声応答を生成しますか？ (y/n): ").lower()
if generate_audio == 'y':
    generate_flag = True
    print("音声応答を生成します。")
else:
    print("音声応答を生成しません。")

# アシスタントのインスタンスを作成
assistant = ChatGPTAssistant(openai_api_key)

print("チャットを開始します。終了するには 'quit' と入力してください。")
print("画像について質問する場合は、'画像：[画像パス]' と入力し、改行して質問を入力してください。")

while True:
    # ユーザー入力の受け取り
    print("\nあなた:")
    user_input = place+"に関する、以下の質問に答えてください。\n"
    # while True:
        # line = input()
        # if line.strip() == "":
        #     break
        # user_input += line + "\n"
    # user_input = user_input.strip()
    line = input()
    user_input += line
    
    if user_input.lower() == 'quit':
        print("チャットを終了します。")
        break
    
    # 応答の生成
    response = assistant.process_chat(user_input)
    
    # 音声応答の生成を確認
    if generate_flag:
        audio_file = assistant.generate_audio_response(response, model, voice)
        print(f"音声ファイルが生成されました: {audio_file}")
    
    print("\nアシスタント:", response)