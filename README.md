# Universal RAG PoC Backend

どの企業（workspace）でも資料を投入すれば、引用付き回答と取り込みレポートを返せる汎用RAGバックエンドです。

## Type B（資産化 / Component PoC）概要
- PoC ID: 2026-02-27-rag-chat-mini
- 目的: ミニマムな再利用コンポーネント（取り込み→検索→回答）を提供し、利用者がコピーして改良を始められる状態にする
- 対象入力: Markdown / テキスト / PDF / DOCX
- 対象出力: テキスト回答（引用付き）、CLI/HTTP両対応を前提
- 改良ポイント（例）: chunk戦略、embedding差し替え、retriever差し替え、reranker追加、prompt/guardrails
- 今回触る改良ポイント: chunkサイズ/overlap、embeddingモデルを環境変数で切り替え可能にする
- 触らない領域: 本番運用（監視・SLA）、UI作り込み、高網羅テスト

### Asset DoD
- Quickstart 3ステップで動作し、サンプル入力で1回確認済みであること
- env/configで差し替え可能（ハードコードしない）
- 再利用ガイドに「向き/不向き」「制約」「落とし穴」が記載されていること

### 置き場所
- 本リポジトリ直下（API/Worker）は既存の汎用RAGバックエンド。
- PoC成果物は `pocs/2026-02-27-rag-chat-mini/`（雛形、REUSE_GUIDE、POC_REPORT）に配置する想定。まだ無い場合はこのパスで作成してください。

## このリポジトリでできること（Overview）
- Workspace単位でドキュメントを隔離し、FastAPIでCRUDとチャット応答を提供
- PDF / DOCX / TXT / MD の非同期取り込み（S3/MinIOへ保存→パース→チャンク→埋め込み→pgvector/FTS登録）
- `/api/workspaces/:wid/chat/query` で引用付き回答を返却。根拠が無い場合は「見つからない」レスポンスにフォールバック
- ingestion reportで失敗ページ・OCR候補・chunk数を確認
- OCR（Gemini）でテキスト抽出できないPDFページを救済、テキストファイルはエンコーディング自動判定
- CLI/HTTP双方の利用を想定し、設定は `.env` で差し替え可能（LLM/Embedding/チャンク戦略）

## 実装スコープ（MVP）
- Workspace単位でのデータ分離（DB/検索/チャットAPIで強制）
- PDF / DOCX / TXT / MD の非同期取り込み
- 取り込み: S3保存 → parse → chunk → embedding → pgvector/FTS 登録
- `/api/workspaces/:wid/chat/query` で引用（chunk_id, page/section, snippet）付き回答
- 根拠なし時は「ソース内に該当情報が見つかりませんでした」を返却
- ingestion report で失敗ページ、OCR候補、chunk数を可視化

## 技術スタック
- Python 3.11+
- FastAPI
- PostgreSQL 15 + pgvector
- SQLAlchemy 2.x + Alembic
- RQ + Redis
- MinIO(S3互換)
- LLM/Embedding: Gemini固定（`gemini-2.5-flash` / `gemini-embedding-001`）

## ディレクトリ
- `app/`: API本体（routers/models/services）
- `worker/`: RQ worker + ingestion job
- `next-chat-ui/`: Next.js製のフロントエンド
- `alembic/`: DBマイグレーション
- `docker-compose.yml`: ローカル一式起動
- `docker-compose.prod.yml`: VPS向け本番構成
- `deploy/Caddyfile`: HTTPS終端とフロント/MinIO公開用のCaddy設定

## 起動方法
まず `.env` を作成します。

```bash
cp .env.example .env
```

その後、バックエンド一式を起動します。

```bash
docker compose up --build
```

起動後:
- API: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

フロントも Docker で起動する場合:
```bash
cp .env.example .env
docker compose --profile frontend up --build
```

起動後:
- フロント: `http://localhost:3000`
- API: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

補足:
- `frontend` サービスは `Next.js` の開発サーバーを Docker 内で動かします。初回だけ `npm ci` が走るので少し待ちます。
- 既定の `docker compose up --build` はこれまで通りバックエンド中心の起動です。フロントは `--profile frontend` を付けたときだけ起動します。
- Google Drive取込を使う場合は、`secrets/google-drive-service-account.json` にサービスアカウントJSONを置いてください。`api` と `worker` はそのディレクトリを `/run/secrets` として参照します。

## 環境変数
最小セット（`.env.example` 参照）:
- `DATABASE_URL`
- `REDIS_URL`
- `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`
- `LLM_PROVIDER`, `LLM_MODEL`
- `GEMINI_API_KEY`, `GEMINI_BASE_URL`
- `PDF_OCR_ENABLED`, `PDF_OCR_MODEL`, `PDF_OCR_MAX_PAGES_PER_DOC`
- `CORS_ORIGINS` (`http://localhost:3000,http://127.0.0.1:3000` 推奨)

### Gemini設定（必須）
`.env` で以下を設定:
- `EMBEDDING_PROVIDER=gemini`
- `EMBEDDING_MODEL=gemini-embedding-001`
- `EMBEDDING_DIM=1536`
- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-2.5-flash`
- `GEMINI_API_KEY=<your_gemini_key>`

反映:
```bash
docker compose up -d --build api worker
```

`docker compose` 利用時は、コンテナ内部接続用に `S3_ENDPOINT=http://minio:9000`、ブラウザ向け公開URLとして `S3_PUBLIC_ENDPOINT=http://localhost:9000` を使うと `DNS_PROBE_FINISHED_NXDOMAIN` を回避できます。

### API認証
`/api/*` は認証なしで利用できます（ローカル開発向け）。

## VPSデプロイ
フロントも含めてVPS 1台へ載せる場合は `docker-compose.prod.yml` を使ってください。構成は `Caddy + Next.js + FastAPI + Worker + PostgreSQL + Redis + MinIO` です。

前提:
- `APP_DOMAIN` と `FILES_DOMAIN` の 2つのDNS名をVPSへ向ける
- VPSの `80/tcp`, `443/tcp` を開ける
- Docker / Docker Compose が使える

手順:
1. `.env.vps.example` を `.env.vps` にコピーして値を埋める
2. 最低でも `APP_DOMAIN`, `FILES_DOMAIN`, `LETSENCRYPT_EMAIL`, `GEMINI_API_KEY`, `CLINIC_PASSWORD`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` を更新する
3. `S3_PUBLIC_ENDPOINT` は必ず `https://<FILES_DOMAIN>` に合わせる
4. 起動する

```bash
cp .env.vps.example .env.vps
docker compose --env-file .env.vps -f docker-compose.prod.yml up -d --build
```

起動後:
- フロント: `https://<APP_DOMAIN>`
- MinIO公開URL: `https://<FILES_DOMAIN>`

補足:
- Caddyが自動でLet's Encrypt証明書を取得します。既存のNginxやApacheが `80/443` を掴んでいる場合は競合します。
- 既存のリバースプロキシを使いたい場合、今回追加したCaddyは外して `frontend:3000` と `minio:9000` を既存プロキシへ繋ぐ代替案もあります。
- Google Drive取込を使う場合は、VPS 上でも `secrets/google-drive-service-account.json` にサービスアカウントJSONを置いてください。`api` と `worker` が `/run/secrets/google-drive-service-account.json` として参照します。

## API
- `GET /api/workspaces`
- `POST /api/workspaces`
- `DELETE /api/workspaces/:wid`
- `GET /api/workspaces/:wid/docs`
- `POST /api/workspaces/:wid/docs/upload` (multipart)
- `GET /api/workspaces/:wid/docs/:docId`
- `GET /api/workspaces/:wid/docs/:docId/ingestion-report`
- `GET /api/workspaces/:wid/docs/:docId/presigned-url`
- `GET /api/workspaces/:wid/chunks/:chunkId`
- `POST /api/workspaces/:wid/chat/query`

## 動作確認例
### 1) workspace作成
```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Corp"}'
```

### 2) ドキュメントアップロード
```bash
curl -X POST "http://localhost:8000/api/workspaces/<wid>/docs/upload" \
  -F "file=@/path/to/manual.pdf"
```

### 3) 取り込み状態とレポート確認
```bash
curl "http://localhost:8000/api/workspaces/<wid>/docs"
curl "http://localhost:8000/api/workspaces/<wid>/docs/<doc_id>/ingestion-report"
```

### 4) チャット問い合わせ
```bash
curl -X POST "http://localhost:8000/api/workspaces/<wid>/chat/query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"有給休暇の繰越上限は？"}'
```

## 実装上の注意
- PDFでテキスト抽出できないページは、`PDF_OCR_ENABLED=true` かつ Gemini APIキーがある場合にOCRを試行します。成功したページは `ocr_used_pages` に記録されます。
- OCRで救済できなかったページは `failed_pages` に `image_only_or_no_text` として記録されます。
- TXT/MDはエンコーディングを自動判定（UTF-8 / CP932 / Shift_JIS / EUC-JP など）し、判定不能時は置換デコードしてタグ (`DECODE_REPLACED`, `POSSIBLE_MOJIBAKE`) を付与します。
- 引用に存在しない `chunk_id` はサーバ側で除外し、引用が空なら「見つからない」レスポンスへ補正します。
- 現在のvector列は `vector(1536)` 前提です。別次元モデルを使う場合はマイグレーション更新が必要です。
- Workspace削除時は配下ドキュメントのオブジェクト（S3/MinIO）も削除してからDBレコードを削除します。
