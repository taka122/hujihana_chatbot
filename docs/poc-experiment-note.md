# 🧪 PoC実験ノート（中間報告）

## 1. 現在の状況 (Status)
* **現在のフェーズ:** Plan B へ移行
* **進捗ステータス:** 遅延
  * 理由: 汎用RAG基盤の実装自体は進んだが、テスト対象のズレと実装二重化の整理が未完了。

## 2. 試行ログ (Try & Error)
* **Plan A の結果:**
  * **事実 (Fact):**
    * `python -m pytest -q` は `5 passed`。ただし対象は `care_rag_poc/*` のみで、`app/*`（現行API/worker系）は直接テストされていない。
    * UIのアップロード許可拡張子に `pptx/xlsx/png/jpg` が含まれる一方、バックエンド取り込みは非対応として `failed` 扱いになる。
    * UIは `GET /docs/{doc_id}/preview` を試すが、バックエンドにはそのエンドポイントがなく、404時に `presigned-url` へフォールバックしている。
    * `next-chat-ui/app/api/chat/route.ts`（旧ルート）と `app/routers/chat.py`（現行ルート）が同居している。
  * **解釈 (Analysis):**
    * 「テストが通っている」事実だけでは、現行の汎用RAG基盤の品質担保にはならない。
    * UIとバックエンドの契約不整合（対応拡張子・プレビューAPI差分）が失敗率と運用混乱の主因。
    * 実装二重化で、障害切り分け・オンボーディング・保守コストが増えている。
    * どちらを本命運用にするかは、リポジトリ情報だけでは不明。
  * **反論・代替案・懸念点:**
    * 反論: 追加機能を先に積むより、まず契約整合とAPI統合テストを先行すべき。
    * 代替案A: Plan A（旧ルート）を一時的に残し、Plan Bをfeature flagで段階移行。
    * 代替案B: Plan Bへ即一本化し、旧ルートは読取専用にして段階廃止。
    * 懸念: 一本化判断を遅らせると、両系統への修正が常態化して開発速度が下がる。
* **Plan B の進捗:**
  * **やったこと:**
    * FastAPI + PostgreSQL(pgvector) + Redis/RQ + MinIO の汎用RAG基盤を実装。
    * Workspace分離、文書アップロード、取り込みレポート、署名URL、チャット問い合わせAPIを実装。
    * 取り込みパイプライン（parse -> chunk -> embedding -> DB登録）をworkerで非同期化。
    * 検索は vector + FTS のhybrid取得を実装。
    * 回答は Gemini 固定構成で実装し、引用なし断定回避のガードを実装。
    * Next.js UIを現行APIに接続（workspace/doc/chat/source viewer）。

## 3. 再現性チェック (Draft Recipe)
* **現時点での環境構築手順:**
  [後で清書するため、箇条書きでOK。コマンドや設定値をメモする]
  1. `docker compose up --build`
  2. ヘルスチェック: `curl http://localhost:8000/healthz`
  3. Workspace作成:
     `curl -X POST http://localhost:8000/api/workspaces -H 'Content-Type: application/json' -d '{"name":"Acme Corp"}'`
  4. ドキュメント投入:
     `curl -X POST "http://localhost:8000/api/workspaces/<wid>/docs/upload" -F "file=@/path/to/manual.pdf"`
  5. 取り込み結果確認:
     `curl "http://localhost:8000/api/workspaces/<wid>/docs"`
     `curl "http://localhost:8000/api/workspaces/<wid>/docs/<doc_id>/ingestion-report"`
  6. チャット問い合わせ:
     `curl -X POST "http://localhost:8000/api/workspaces/<wid>/chat/query" -H 'Content-Type: application/json' -d '{"query":"有給休暇の繰越上限は？"}'`
  7. `.env` に Gemini 用APIキー（`GEMINI_API_KEY`）を設定して再起動。
  8. 注意: `pptx/xlsx/png/jpg` は現時点では取り込み失敗が仕様。OCR/PPTX/XLSX対応は未実装。
  9. 不明: `.env.example` の実ファイル有無と、運用時の正式な環境変数テンプレート整備状況。

## 4. 次のアクション
* **次の60時間でやること:**
  * `app/*` 向けAPI/worker統合テストを追加（upload -> ingest -> query のE2E最小1本を必須化）。
  * UIの受け付け拡張子をバックエンド対応範囲に合わせるか、非対応時の事前警告を追加。
  * `preview` APIを実装するか、UIを `presigned-url` 前提へ整理して仕様を一本化。
  * 旧実装（`care_rag_poc/*` と `next-chat-ui/app/api/chat/route.ts`）の扱いを決定し、README導線を統一。
  * 方針意思決定（Plan B一本化 or 段階移行）を48時間以内に確定。
  * ヘルプが必要な点:
    * 本命運用経路の意思決定（PO/Tech Lead）
    * 非対応フォーマット（OCR/PPTX/XLSX）を今回スコープに含めるかの判断
