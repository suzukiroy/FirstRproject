#!/bin/bash
set -e

# ANTHROPIC_API_KEY が未設定なら入力を求める
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY を入力してください（入力した文字は表示されません）:"
  read -rs ANTHROPIC_API_KEY
  export ANTHROPIC_API_KEY
fi

# 依存パッケージをインストール（初回のみ時間がかかります）
pip install -q -r requirements.txt

# ローカルIPを表示（スマホからのアクセス用）
echo ""
echo "========================================="
echo "  アプリを起動します"
LOCAL_IP=$(python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    print(s.getsockname()[0])
finally:
    s.close()
" 2>/dev/null || echo "localhost")
echo "  PC:      http://localhost:5000"
echo "  スマホ:   http://${LOCAL_IP}:5000"
echo "  ※ スマホとPCが同じWi-Fiに接続している必要があります"
echo "========================================="
echo ""

python3 app.py
