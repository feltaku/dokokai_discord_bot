# ベースイメージ
FROM python:3.11

# 作業ディレクトリ
WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# 実行コマンド
CMD ["python", "main.py"]
