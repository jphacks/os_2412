class ImageAnalyzer:
    def __init__(self, client):
        self.client = client

    def analyze_image(self, image_data, latitude, longitude):
        """画像を分析し、場所の説明と名称を取得する"""
        try:
            # 詳細な説明を取得するためのメッセージ
            description_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"この画像は緯度{latitude}、経度{longitude}で撮影されました。"
                                f"画像の内容と撮影された場所について、名称を交えて詳しく説明してください。緯度と経度は説明に含めないでください。"
                                f"歴史的背景や周辺の観光スポット、危険な場所、治安、注意点についても具体的に触れてください。"
                                f"説明は日本語で、ガイドが観光客に説明するような親しみやすい口調でお願いします。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }

            # 場所の名称のみを取得するためのメッセージ
            place_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"緯度{latitude}、経度{longitude}で撮影されたこの場所の名前を、単語のみの形で答えてください。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }

            # 説明の取得
            description_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[description_message],
                max_tokens=500
            )

            # 場所名の取得
            place_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[place_message],
                max_tokens=100
            )

            description = description_response.choices[0].message.content
            place = place_response.choices[0].message.content.strip()

            # 音声の生成
            audio_response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=description
            )

            return {
                'description': description,
                'place': place,
                'audio_response': audio_response
            }

        except Exception as e:
            raise Exception(f"画像分析エラー: {str(e)}")