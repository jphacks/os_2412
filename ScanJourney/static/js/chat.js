// static/js/chat.js

class ChatManager {
    constructor() {
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.audioEnabled = document.getElementById('audio-enabled');
        this.loading = document.getElementById('loading');
        this.errorMessage = document.getElementById('error-message');
        this.currentAudio = null;

        this.initializeEventListeners();
        this.initialScroll();
    }

    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    formatTimestamp(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString('ja-JP');
    }

    addMessage(message, type, timestamp) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.textContent = message;
        messageDiv.appendChild(contentDiv);
        
        if (timestamp) {
            const timestampDiv = document.createElement('div');
            timestampDiv.className = 'timestamp';
            timestampDiv.textContent = this.formatTimestamp(timestamp);
            messageDiv.appendChild(timestampDiv);
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, 5000);
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        this.messageInput.value = '';
        this.sendButton.disabled = true;
        this.loading.style.display = 'block';
        this.errorMessage.style.display = 'none';

        try {
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    with_audio: this.audioEnabled.checked
                })
            });

            const data = await response.json();
            if (data.success) {
                this.updateChatHistory(data);
                this.playAudioIfAvailable(data);
            } else {
                this.showError(data.error || 'エラーが発生しました。');
            }
        } catch (error) {
            this.showError('通信エラーが発生しました。');
        } finally {
            this.sendButton.disabled = false;
            this.loading.style.display = 'none';
        }
    }

    updateChatHistory(data) {
        this.chatMessages.innerHTML = '';
        data.history.forEach(msg => {
            this.addMessage(msg.content, msg.type, msg.timestamp);
        });
    }

    playAudioIfAvailable(data) {
        if (data.audio_file) {
            if (this.currentAudio) {
                this.currentAudio.pause();
            }
            this.currentAudio = new Audio(data.audio_file);
            this.currentAudio.play();
        }
    }

    initialScroll() {
        this.scrollToBottom();
    }
}

// DOMの読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', () => {
    new ChatManager();
});