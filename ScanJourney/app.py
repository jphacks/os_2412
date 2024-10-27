from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import os
from datetime import datetime
import json
from utils.image_analyzer import ImageAnalyzer
from utils.metadata_manager import MetadataManager
from utils.gui_chat_manager import launch_gui_chat
from openai import OpenAI
from dotenv import load_dotenv

os.environ["PYTHONIOENCODING"] = "utf-8"

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
    # 画像ファイルとそれに対応するメタデータを取得
    images = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.startswith('image') and filename.endswith(('png', 'jpg', 'jpeg')):
            # メタデータを取得
            image_metadata = metadata_manager.get_image_data_by_filename(filename)
            
            # もしメタデータが存在すれば、画像データと一緒にリストに追加
            if image_metadata:
                # 画像のタイムスタンプを整形
                timestamp = datetime.fromisoformat(image_metadata['timestamp']).strftime('%Y年%m月%d日 %H時%M分')
                images.append({
                    'filename': filename,
                    'place_name': image_metadata['place_name'],
                    'timestamp': timestamp
                })

    return render_template('album.html', images=images)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        image_data = data['image']
        latitude = data['latitude']
        longitude = data['longitude']

        # Base64データの処理
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # 画像分析の実行
        result = image_analyzer.analyze_image(image_data, latitude, longitude)

        # 画像の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"image_{timestamp}.jpg"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        
        # Base64データを画像として保存
        import base64
        image_binary = base64.b64decode(image_data)
        with open(image_path, 'wb') as f:
            f.write(image_binary)

        # 音声ファイルの保存
        audio_filename = f"audio_{timestamp}.wav"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        with open(audio_path, 'wb') as audio_file:
            audio_file.write(result['audio_response'].content)

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

        return jsonify({
            'success': True,
            'image_id': image_id,
            'description': result['description'],
            'place': result['place'],
            'audio_file': f"/static/uploads/{audio_filename}",
            'image_file': f"/static/uploads/{image_filename}"
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        app.logger.error(f"Analysis error: {error_detail}")
        return jsonify({
            'success': False,
            'error': f"分析中にエラーが発生しました: {str(e)}"
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
            model="gpt-4-turbo-preview",
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

@app.route('/launch_gui_chat/<image_id>')
def launch_gui_chat_route(image_id):
    image_data = metadata_manager.get_image_data(image_id)
    if not image_data:
        return jsonify({'success': False, 'error': '画像が見つかりません'})

    # GUIチャットの起動
    launch_gui_chat(
        openai_client,
        image_data['place_name'],
        image_data['description']
    )

    return jsonify({'success': True, 'message': 'GUIチャットを起動しました'})

if __name__ == '__main__':
    app.run(debug=True)