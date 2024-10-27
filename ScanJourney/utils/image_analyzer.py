# utils/image_analyzer.py

import json

class ImageAnalyzer:
    def __init__(self, client):
        self.client = client

    def analyze_image(self, image_data, latitude, longitude):
        """画像を分析し、場所の説明と名称を取得する"""
        try:
            # 詳細な説明を取得するためのメッセージ
            description_prompt = (
                f"この画像は緯度{latitude}、経度{longitude}で撮影されました。"
                f"画像の内容と撮影された場所について、名称を交えて詳しく説明してください。緯度と経度は説明に含めないでください。"
                f"歴史的背景や周辺の観光スポット、危険な場所、治安、注意点についても具体的に触れてください。"
                f"説明は日本語で、ガイドが観光客に説明するような親しみやすい口調でお願いします。"
            )

            # 場所の名称のみを取得するためのメッセージ
            place_prompt = (
                f"緯度{latitude}、経度{longitude}で撮影されたこの場所の名前を、"
                f"単語のみの形で答えてください。"
            )

            # メッセージの構築
            description_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": description_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }

            place_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": place_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }

            # APIリクエストの実行
            description_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[description_message],
                max_tokens=500
            )

            place_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[place_message],
                max_tokens=100
            )

            description = description_response.choices[0].message.content
            place = place_response.choices[0].message.content.strip()

            # 音声生成用のテキストをUTF-8でエンコード
            description_for_audio = description.encode('utf-8').decode('utf-8')

            # 音声の生成
            audio_response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=description_for_audio
            )

            return {
                'description': description,
                'place': place,
                'audio_response': audio_response
            }

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Error details: {error_detail}")  # デバッグ用
            raise Exception(f"画像分析エラー: {str(e)}\n{error_detail}")