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
- LLM/Embedding: Gemini固定（`gemini-2.0-flash` / `gemini-embedding-001`）

## ディレクトリ
- `app/`: API本体（routers/models/services）
- `worker/`: RQ worker + ingestion job
- `alembic/`: DBマイグレーション
- `docker-compose.yml`: ローカル一式起動

## 起動方法
```bash
docker compose up --build
```

起動後:
- API: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

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
- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-2.0-flash`
- `GEMINI_API_KEY=<your_gemini_key>`

反映:
```bash
docker compose up -d --build api worker
```

`docker compose` 利用時は、コンテナ内部接続用に `S3_ENDPOINT=http://minio:9000`、ブラウザ向け公開URLとして `S3_PUBLIC_ENDPOINT=http://localhost:9000` を使うと `DNS_PROBE_FINISHED_NXDOMAIN` を回避できます。

### API認証
`/api/*` は認証なしで利用できます（ローカル開発向け）。

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

## トラブルシューティング

### PDFを開こうとするとエラーになる（DNS_PROBE_FINISHED_NXDOMAIN / 接続できない）

**原因**: PDFプレビューはMinIOの presigned URL をブラウザで直接開く仕組みです。
`S3_PUBLIC_ENDPOINT` が設定されていないとAPIが `http://minio:9000/...` という内部ホスト名のURLを返し、ブラウザから到達できません。

**修正手順**:
1. `.env` に以下を追加（または `.env.example` を `.env` にコピーして編集）:
   ```
   S3_PUBLIC_ENDPOINT=http://localhost:9000
   ```
2. コンテナを再起動:
   ```bash
   docker compose up -d --build api
   ```

docker-compose.yml ではデフォルトで `S3_PUBLIC_ENDPOINT=http://localhost:9000` が設定されています。
直接 Python で起動している場合は `.env` への追記が必要です。

### PDFアップロード後に "Storage unavailable" エラーが出る

**原因**: MinIO が起動していないか、`S3_BUCKET` が存在しない可能性があります。

**確認手順**:
1. MinIO が起動しているか確認: `docker compose ps`
2. MinIO Console (`http://localhost:9001`) でバケット `rag-documents` の存在を確認
3. バケットがない場合は自動作成されますが、MinIO への接続情報（`S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`）を確認してください

### チャット応答が遅い / Gemini API コストを抑えたい

以下の環境変数で主要なコストドライバーを調整できます:

| 環境変数 | デフォルト | 説明 |
|---|---|---|
| `PDF_OCR_MAX_PAGES_PER_DOC` | `5` | OCR（Gemini Vision）を呼ぶ最大ページ数。値を下げるとコスト削減 |
| `VECTOR_TOP_K` | `10` | ベクトル検索で取得するチャンク数 |
| `KEYWORD_TOP_K` | `10` | キーワード検索で取得するチャンク数 |
| `ANSWER_CONTEXT_CHUNKS` | `5` | LLMに渡すチャンク数（小さいほど安く速い） |

OCR を完全に無効化したい場合は `PDF_OCR_ENABLED=false` を設定してください。

### ブラウザのポップアップブロックで「内容を開く」が動かない

ブラウザの設定で `http://localhost:3000` のポップアップを許可してください。

---

## 実装上の注意
- PDFでテキスト抽出できないページは、`PDF_OCR_ENABLED=true` かつ Gemini APIキーがある場合にOCRを試行します。成功したページは `ocr_used_pages` に記録されます。
- OCRで救済できなかったページは `failed_pages` に `image_only_or_no_text` として記録されます。
- TXT/MDはエンコーディングを自動判定（UTF-8 / CP932 / Shift_JIS / EUC-JP など）し、判定不能時は置換デコードしてタグ (`DECODE_REPLACED`, `POSSIBLE_MOJIBAKE`) を付与します。
- 引用に存在しない `chunk_id` はサーバ側で除外し、引用が空なら「見つからない」レスポンスへ補正します。
- 現在のvector列は `vector(1536)` 前提です。別次元モデルを使う場合はマイグレーション更新が必要です。
- Workspace削除時は配下ドキュメントのオブジェクト（S3/MinIO）も削除してからDBレコードを削除します。
