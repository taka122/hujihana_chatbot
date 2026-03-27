# hujihana_chatbot

Gemini を使った RAG チャットのローカル開発用リポジトリです。現在の実装は、FastAPI バックエンド、RQ worker、PostgreSQL + pgvector、Redis、MinIO、Next.js フロントエンドで構成されています。

この README は、今このリポジトリに入っている実装に合わせて書いています。以前の PoC 計画メモ寄りの説明は落とし、起動方法と制約を中心に整理しています。

## できること

- Workspace 単位でドキュメントを分離して管理
- PDF / DOCX / TXT / MD をアップロードして非同期取り込み
- 取り込み時に S3 互換ストレージへ保存し、テキスト抽出、チャンク化、埋め込み生成、pgvector 登録を実行
- `/api/workspaces/{wid}/chat/query` で引用付き回答を返却
- 取り込みレポートで失敗ページ、OCR 使用ページ、chunk 数を確認
- Next.js UI からチャット、アップロード、レポート確認
- `care_rag_poc/` 配下の簡易 CLI PoC を別経路で実行

## 現在の構成

- `app/`: FastAPI 本体
- `worker/`: RQ worker と ingestion job
- `alembic/`: DB マイグレーション
- `next-chat-ui/`: Next.js フロントエンド
- `care_rag_poc/`: 介護事業所サンプルデータ向けの CLI PoC
- `data/`: CLI PoC 用サンプルデータ
- `tests/`: 単体テスト

## サポート形式

取り込み対応:

- PDF
- DOCX
- TXT
- MD

未対応:

- PPT / PPTX
- XLS / XLSX
- 画像ファイル単体

未対応形式は worker 側で `failed` 扱いになります。

## 技術スタック

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL 15 + pgvector
- Redis + RQ
- MinIO
- Next.js 14
- Gemini (`gemini-2.0-flash`, `gemini-embedding-001`)

## 前提

- Docker / Docker Compose
- Node.js / npm
- Gemini API Key

## 環境変数

`.env` は `.gitignore` に含まれており、このリポジトリには現在 `.env.example` を置いていません。まずルートに `.env` を作成してください。

Docker Compose 前提なら最低限これで足ります。

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
EMBEDDING_MODEL=gemini-embedding-001
LLM_MODEL=gemini-2.0-flash
S3_PUBLIC_ENDPOINT=http://localhost:9000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

補足:

- Compose では DB / Redis / MinIO の接続先は `docker-compose.yml` 側でコンテナ向け値を注入しています。
- API / worker をホスト上で直接起動するなら、`DATABASE_URL` / `REDIS_URL` / `S3_ENDPOINT` などを `localhost` ベースで別途設定してください。
- Gemini API Key は UI の設定画面から `X-GEMINI-API-Key` ヘッダとして個別送信することもできます。

フロントエンド側は必要なら `next-chat-ui/.env.local` を作成してください。

```env
API_PROXY_TARGET=http://localhost:8000
```

未設定でも `http://localhost:8000` が既定値です。

## 起動方法

### 1. バックエンド一式を起動

```bash
docker compose up -d --build
```

起動確認:

```bash
curl http://localhost:8000/healthz
```

期待値:

```json
{"status":"ok"}
```

### 2. フロントエンドを起動

```bash
cd next-chat-ui
npm ci
npm run dev
```

ブラウザ:

- UI: `http://localhost:3000`
- API Swagger: `http://localhost:8000/docs`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

`3000` が埋まっている場合:

```bash
cd next-chat-ui
PORT=3001 npm run dev
```

その場合の UI URL は `http://localhost:3001` です。

## 停止方法

バックエンド停止:

```bash
docker compose down --remove-orphans
```

フロントエンド停止:

- `npm run dev` を実行しているターミナルで `Ctrl+C`

## API 一覧

認証はありません。ローカル開発向けの前提です。

- `GET /api/workspaces`
- `POST /api/workspaces`
- `DELETE /api/workspaces/{wid}`
- `GET /api/workspaces/{wid}/docs`
- `POST /api/workspaces/{wid}/docs/upload`
- `GET /api/workspaces/{wid}/docs/{doc_id}`
- `DELETE /api/workspaces/{wid}/docs/{doc_id}`
- `GET /api/workspaces/{wid}/docs/{doc_id}/ingestion-report`
- `GET /api/workspaces/{wid}/docs/{doc_id}/presigned-url`
- `GET /api/workspaces/{wid}/chunks/{chunk_id}`
- `POST /api/workspaces/{wid}/chat/query`
- `GET /healthz`

## 使い方

### Workspace 作成

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"name":"藤花歯科クリニック"}'
```

### ドキュメントアップロード

```bash
curl -X POST "http://localhost:8000/api/workspaces/<wid>/docs/upload" \
  -F "file=@/path/to/manual.pdf"
```

### 取り込み状況確認

```bash
curl "http://localhost:8000/api/workspaces/<wid>/docs"
curl "http://localhost:8000/api/workspaces/<wid>/docs/<doc_id>/ingestion-report"
```

### チャット問い合わせ

```bash
curl -X POST "http://localhost:8000/api/workspaces/<wid>/chat/query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"有給休暇の繰越上限は？"}'
```

Gemini API Key をリクエスト単位で上書きする場合:

```bash
curl -X POST "http://localhost:8000/api/workspaces/<wid>/chat/query" \
  -H 'Content-Type: application/json' \
  -H 'X-GEMINI-API-Key: your_gemini_api_key' \
  -d '{"query":"有給休暇の繰越上限は？"}'
```

## フロントエンドについて

- Next.js 側は `/api/backend/*` へアクセスし、サーバー側で FastAPI にプロキシします。
- `localhost` / `127.0.0.1` 差異による CORS 事故を減らすための構成です。
- UI の設定画面から Gemini API Key を保存すると、ブラウザから `X-GEMINI-API-Key` が付与されます。

## CLI PoC

`care_rag_poc/` は本体 API と別系統の簡易 PoC です。`data/facilities_sample.csv` を使います。

rule ベースで起動:

```bash
python3 -m care_rag_poc.cli --backend rule
```

Gemini を使う場合:

```bash
python3 -m care_rag_poc.cli --backend rag --gemini-api-key your_gemini_api_key
```

## テスト

現時点では以下が通ることを確認しています。

```bash
python3 -m pytest -q
```

## 実装上の注意

- Gemini API Key が無いと、埋め込み生成、回答生成、OCR は実質動きません。
- PDF はテキスト抽出が弱いページに対して Gemini OCR を試します。
- OCR で救済できなかったページは `failed_pages` に `image_only_or_no_text` として残ります。
- TXT / MD は文字コード自動判定を行い、置換が入った場合はタグを付けます。
- ベクトル列は `1536` 次元前提です。別次元モデルを使うならマイグレーションも修正が必要です。
- Workspace 削除時は、関連するオブジェクトを MinIO から削除してから DB レコードを消します。

## よくあるハマりどころ

### Gemini が効かない

- `GEMINI_API_KEY` が未設定
- UI に保存した API Key が不正
- コンテナ再起動前に `.env` だけ更新した

`.env` を変えたら再反映してください。

```bash
docker compose down --remove-orphans
docker compose up -d --build
```

### Docker 起動時に container name conflict が出る

このリポジトリの `docker-compose.yml` は `rag-api` など固定 `container_name` を使っています。別 checkout や別プロジェクトで同名コンテナが起動中だと衝突します。

まず既存コンテナを確認してください。

```bash
docker ps -a | grep '^.*rag-'
```

必要なら不要な側を止めるか、compose 側の `container_name` を見直してください。

### UI は上がるがデータ取得できない

- バックエンドが `http://localhost:8000` で動いていない
- `API_PROXY_TARGET` が別 URL を向いている
- `next-chat-ui` だけ起動して backend を起動していない
