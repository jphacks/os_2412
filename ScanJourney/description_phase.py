from flask import Flask, render_template, request, jsonify, session, url_for
import os
from openai import OpenAI
import base64
from datetime import datetime
from PIL import Image
import io
import json

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key')  # 必ず環境変数で設定
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

class ImageAnalyzer:
    def __init__(self, openai_api_key):
        self.client = OpenAI(api_key=openai_api_key)

    def analyze_image(self, image_data, latitude, longitude):
        try:
            messages = [
                  {
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
              ]
            
            messages2 = [
                  {
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
              ]

            # 画像分析の実行
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500
            )
            # response = self.client.chat.completions.create(
            #     model="gpt-4-vision-preview",
            #     messages=messages
            # )

            response2 = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages2,
                max_tokens=100
            )

            description = response.choices[0].message.content
            place = response2.choices[0].message.content

            audio_response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=response.choices[0].message.content
            )

            return description, place, audio_response
        except Exception as e:
            raise Exception(f"画像分析エラー: {str(e)}")

class ImageManager:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.metadata_file = os.path.join(upload_folder, 'metadata.json')
        self.load_metadata()

    # 既存のメソッドは変更なし

    def save_image(self, image_data, latitude, longitude, description, place):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"image_{timestamp}.jpg"
            image_path = os.path.join(self.upload_folder, image_filename)

            # Base64データをデコードして画像を保存
            image_binary = base64.b64decode(image_data.split(',')[1])
            with open(image_path, 'wb') as f:
                f.write(image_binary)

            # メタデータを保存
            self.metadata[image_filename] = {
                'timestamp': timestamp,
                'latitude': latitude,
                'longitude': longitude,
                'description': description,
                'place': place,
                'path': f"/static/uploads/{image_filename}"
            }
            self.save_metadata()

            return image_filename
        except Exception as e:
            raise Exception(f"画像保存エラー: {str(e)}")

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        image_data = data['image']
        latitude = data['latitude']
        longitude = data['longitude']

        # 画像分析と音声生成
        description, place, audio_response = analyzer.analyze_image(
            image_data.split(',')[1] if ',' in image_data else image_data,
            latitude,
            longitude
        )

        # 画像の保存
        image_filename = image_manager.save_image(
            image_data,
            latitude,
            longitude,
            description,
            place
        )

        # 音声ファイルの保存
        audio_filename = f"audio_{image_filename.replace('.jpg', '.wav')}"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        audio_response.stream_to_file(audio_path)

        # レスポンスの作成
        response_data = {
            'success': True,
            'description': description,
            'place': place,
            'audio_file': f"/static/uploads/{audio_filename}",
            'image_file': f"/static/uploads/{image_filename}"
        }

        # セッションに履歴を保存
        if 'history' not in session:
            session['history'] = []
        session['history'].append({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'image': response_data['image_file'],
            'description': description,
            'place': place,
            'audio': response_data['audio_file'],
            'latitude': latitude,
            'longitude': longitude
        })

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500