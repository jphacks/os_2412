from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import os
from datetime import datetime
import json
from utils.image_analyzer import ImageAnalyzer
from utils.metadata_manager import MetadataManager
from openai import OpenAI
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 初期化
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
image_analyzer = ImageAnalyzer(openai_client)
metadata_manager = MetadataManager('static/uploads/metadata.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/album')
def album():
    images = metadata_manager.get_all_images()
    return render_template('album.html', images=images)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        image_data = data['image']
        latitude = data['latitude']
        longitude = data['longitude']

        # 画像分析の実行
        result = image_analyzer.analyze_image(image_data, latitude, longitude)

        # 画像の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"image_{timestamp}.jpg"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        
        # Base64データをデコードして画像を保存
        import base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_binary = base64.b64decode(image_data)
        with open(image_path, 'wb') as f:
            f.write(image_binary)

        # 音声ファイルの保存
        audio_filename = f"audio_{timestamp}.wav"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        result['audio_response'].stream_to_file(audio_path)

        # メタデータの保存
        image_id = metadata_manager.save_image_data({
            'timestamp': datetime.now().isoformat(),
            'image_path': f"/static/uploads/{image_filename}",
            'audio_path': f"/static/uploads/{audio_filename}",
            'description': result['description'],
            'place_name': result['place'],
            'latitude': latitude,
            'longitude': longitude
        })

        # チャットの初期化
        session['chat_context'] = {
            'image_id': image_id,
            'place_name': result['place'],
            'description': result['description'],
            'latitude': latitude,
            'longitude': longitude
        }
        
        session['chat_history'] = [{
            "type": "assistant",
            "content": result['description'],
            "timestamp": datetime.now().isoformat()
        }]

        return jsonify({
            'success': True,
            'image_id': image_id,
            'description': result['description'],
            'place': result['place'],
            'audio_file': f"/static/uploads/{audio_filename}",
            'image_file': f"/static/uploads/{image_filename}"
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/chat/<image_id>')
def chat(image_id):
    # メタデータから画像情報を取得
    image_data = metadata_manager.get_image_data(image_id)
    if not image_data:
        return redirect(url_for('index'))
    
    # チャットのコンテキストをセッションに保存
    session['chat_context'] = {
        'image_id': image_id,
        'place_name': image_data['place_name'],
        'description': image_data['description'],
        'latitude': image_data['latitude'],
        'longitude': image_data['longitude']
    }
    
    # チャット履歴の初期化（初回説明を含める）
    if 'chat_history' not in session:
        session['chat_history'] = [{
            "type": "assistant",
            "content": image_data['description'],
            "timestamp": datetime.now().isoformat()
        }]
    
    return render_template('chat.html', 
                         image_data=image_data,
                         chat_history=session['chat_history'])

@app.route('/chat/message', methods=['POST'])
def chat_message():
    try:
        data = request.get_json()
        message = data['message']
        with_audio = data.get('with_audio', False)
        context = session.get('chat_context')
        chat_history = session.get('chat_history', [])

        if not context:
            raise Exception("チャットセッションが見つかりません")

        # ユーザーメッセージを履歴に追加
        chat_history.append({
            "type": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # GPTへの問い合わせ
        messages = [
            {
                "role": "system",
                "content": (
                    f"あなたは{context['place_name']}の観光ガイドです。"
                    f"以下の説明に基づいて回答してください：\n{context['description']}"
                )
            }
        ]

        # チャット履歴の追加
        for msg in chat_history:
            role = "assistant" if msg["type"] == "assistant" else "user"
            messages.append({
                "role": role,
                "content": msg["content"]
            })

        # レスポンス生成
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500
        )

        response_text = response.choices[0].message.content

        # アシスタントの応答を履歴に追加
        chat_history.append({
            "type": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })

        # セッションに履歴を保存
        session['chat_history'] = chat_history

        result = {
            'success': True,
            'message': response_text,
            'history': chat_history
        }

        # 音声の生成（オプション）
        if with_audio:
            audio_response = openai_client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=response_text
            )
            
            audio_filename = f"chat_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
            audio_response.stream_to_file(audio_path)
            
            result['audio_file'] = f"/static/uploads/{audio_filename}"

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)