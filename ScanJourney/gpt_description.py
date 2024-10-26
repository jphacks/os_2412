from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
from openai import OpenAI
import requests
from PIL import Image
import io
from gtts import gTTS
from datetime import datetime
import base64

class LocationImageAnalyzer:
    def __init__(self, openai_api_key):
        self.client = OpenAI(api_key=openai_api_key)

    def encode_image_to_base64(self, image_path):
        """画像をbase64エンコードする"""
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

            # base64エンコード
            base64_encoded = base64.b64encode(img_byte_arr).decode('utf-8')
            return base64_encoded

    def analyze_location_and_image(self, image_path, latitude, longitude, model, voice):
        """画像と位置情報を分析する"""
        try:
            # 画像をエンコード
            image_data = self.encode_image_to_base64(image_path)
            messages = [
                  {
                      "role": "user",
                      "content": [
                          {
                              "type": "text",
                              "text": f"この画像は緯度{latitude}、経度{longitude}で撮影されました。"
                                      f"画像の内容と撮影された場所について、名称を交えて詳しく説明してください。緯度と経度は説明に含めないでください。"
                                      f"歴史的背景や周辺の観光スポット、危険な場所、治安についても具体的に触れてください。"
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

            response2 = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages2,
                max_tokens=100
            )

            if model == "gpt-4o-mini":
                # GPT-4Vによる分析
                description = response.choices[0].message.content
                place = response2.choices[0].message.content
                return description, place
            
            else:
                try:
                    description = response.choices[0].message.content
                    place = response2.choices[0].message.content

                    # GPT-4V-Audio-Previewによる音声生成
                    audio_response = self.client.audio.speech.create(
                        model="tts-1",  # TTSモデルを使用
                        voice=voice,   # 音声の種類
                        input=description  # 生成したテキスト
                    )

                    # 出力ディレクトリが存在しない場合は作成
                    output_dir = "audio_output"
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    # ファイル名に現在時刻を含める
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    audio_file = os.path.join(output_dir, f"description_{timestamp}.wav")

                    # 音声を保存
                    audio_response.stream_to_file(audio_file)

                    print(f"音声ファイルを生成しました: {audio_file}")
                    return {"description": description, "audio_file": audio_file, "place": place}

                except Exception as e:
                    return f"音声生成でエラーが発生しました: {str(e)}"

        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def generate_audio(self, text, model, output_dir="audio_output"):
        """テキストを音声に変換する"""
        try:
            # 出力ディレクトリが存在しない場合は作成
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # ファイル名に現在時刻を含める
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = os.path.join(output_dir, f"description_{timestamp}.wav")

            # テキストを音声に変換
            tts = gTTS(text=text, lang='ja', slow=False)
            tts.save(audio_file)

            print(f"音声ファイルを生成しました: {audio_file}")
            return audio_file

        except Exception as e:
            return f"音声生成でエラーが発生しました: {str(e)}"


# OpenAI APIキーを設定
openai_api_key = os.getenv("OpenAI_API_key")
model = "gpt-4o-mini"
# model = "gpt-4o-audio-preview"
# voice = "alloy"
voice = "nova"

# 画像パスと位置情報を設定
image_path = "/content/mohumohu.jpeg"
latitude = 27.329167
longitude = 68.138889

# アナライザーのインスタンスを作成
analyzer = LocationImageAnalyzer(openai_api_key)

if model == "gpt-4o-mini":
    # 画像と位置情報を分析
    description, place = analyzer.analyze_location_and_image(image_path, latitude, longitude, model, voice)

    # 音声を生成
    audio_file = analyzer.generate_audio(description, model)
    print(f"音声ファイルが {audio_file} に保存されました")

    print("場所:", place)
    print("説明:", description)

else:
    # 画像と位置情報を分析して音声生成
    result = analyzer.analyze_location_and_image(image_path, latitude, longitude, model, voice)
    place = result["place"]
    if isinstance(result, dict):
        print("場所:", result["place"])
        print("説明:", result["description"])
        print(f"音声ファイルが {result['audio_file']} に保存されました")
    else:
        print(result)  # エラーメッセージ

