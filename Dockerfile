# リポ直下に置く
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存インストール（キャッシュ効く順番）
COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt

# アプリ一式をコピー（api/, params/, data/ なども含む）
COPY . .

# FastAPI 起動（api/main.py に app = FastAPI() がある想定）
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
