import tkinter as tk
from tkinter import scrolledtext
from threading import Thread
from openai import OpenAI
import queue

class GuiChatManager:
    def __init__(self, openai_client, place_name, description):
        self.openai_client = openai_client
        self.messages_queue = queue.Queue()
        self.root = None
        self.chat_window = None
        self.user_entry = None
        self.messages = [
            {
                "role": "system",
                "content": (
                    f"あなたは{place_name}の観光ガイドです。"
                    f"以下の説明に基づいて回答してください：\n{description}"
                )
            }
        ]

    def create_window(self):
        self.root = tk.Tk()
        self.root.title(f"観光案内チャット")
        self.root.geometry("500x500")

        # チャットウィンドウの作成
        self.chat_window = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            state='normal',
            height=20,
            width=50
        )
        self.chat_window.pack(padx=10, pady=10)
        self.chat_window.insert(tk.END, "ガイド: いらっしゃいませ！ご案内させていただきます。\n")

        # 入力欄の作成
        self.user_entry = tk.Entry(self.root, width=40)
        self.user_entry.pack(pady=10)
        self.user_entry.bind("<Return>", lambda event: self.send_message())

        # 送信ボタンの作成
        send_button = tk.Button(self.root, text="送信", command=self.send_message)
        send_button.pack()

        # 音声切り替えチェックボックス
        self.audio_var = tk.BooleanVar()
        audio_check = tk.Checkbutton(
            self.root, 
            text="音声を有効にする", 
            variable=self.audio_var
        )
        audio_check.pack(pady=5)

    def send_message(self):
        user_input = self.user_entry.get()
        if not user_input.strip():
            return

        if user_input.lower() in ['exit', 'quit']:
            self.root.quit()
            return

        # ユーザーメッセージの表示
        self.chat_window.insert(tk.END, f"あなた: {user_input}\n")
        self.user_entry.delete(0, tk.END)

        # メッセージの追加
        self.messages.append({"role": "user", "content": user_input})

        # 非同期でレスポンスを取得
        Thread(target=self.get_bot_response).start()

    def get_bot_response(self):
        try:
            # GPT-4からの応答を取得
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=self.messages,
                max_tokens=500
            )

            bot_message = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": bot_message})

            # 音声生成（オプション）
            if self.audio_var.get():
                try:
                    audio_response = self.openai_client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=bot_message
                    )
                    # 音声の再生（実装は省略）
                except Exception as e:
                    print(f"音声生成エラー: {str(e)}")

            # GUIの更新をメインスレッドで実行
            self.root.after(0, self.update_chat_window, bot_message)

        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            self.root.after(0, self.update_chat_window, error_message)

    def update_chat_window(self, message):
        self.chat_window.insert(tk.END, f"ガイド: {message}\n")
        self.chat_window.see(tk.END)

    def run(self):
        self.create_window()
        self.root.mainloop()

def launch_gui_chat(openai_client, place_name, description):
    """GUIチャットを別スレッドで起動する関数"""
    chat_manager = GuiChatManager(openai_client, place_name, description)
    Thread(target=chat_manager.run).start()
    return chat_manager