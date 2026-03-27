# PoC検証計画（ドラフト）

## 1. 基本情報
- **実施者名:** 不明（要記入）
- **検証対象ツール:** Universal RAG PoC（FastAPI + PostgreSQL/pgvector + Redis/RQ + MinIO + Next.js UI）
- **カテゴリ:** Agent
- **開始日:** 2026/02/18

## 2. ゴールと成功定義 (Exit Criteria)
- **解決する課題:**
  - 資料投入から根拠付き回答までを、workspace分離を保ったまま一貫運用できるかを検証する。
  - 現状の課題は、UI/Backend契約の不整合（対応拡張子・preview API）と、旧実装/新実装の二重運用による保守負荷。
- **成功の基準 (KPI):**
  - 対応フォーマット（pdf/docx/txt/md）の取り込み成功率: 90%以上
  - `POST /api/workspaces/{wid}/chat/query` の p95 応答時間: 8秒以内（ローカル検証条件）
  - 回答の引用付与率: 95%以上（断定回答時）
  - 統合テスト（upload -> ingest -> query）: 最低1本をCIで常時Pass
  - 注記: 閾値は現時点では仮説。運用要件確定後に再設定が必要。
- **撤退ライン:**
  - 平均APIコストが 100円/問い合わせ を継続的に超える場合
  - 対応フォーマット取り込み失敗率が 30% を超えて改善見込みが薄い場合
  - 引用なし断定回答が 5% を超え、ガード強化でも収束しない場合

## 3. 検証アプローチ (Hypothesis)
- **Plan A (王道):**
  - 現行実装をベースに、API契約整合と統合テストを先行して品質を固定する。
  - 具体: 対応拡張子のUI表示修正、`preview` APIの実装または仕様統一、E2E追加。
- **Plan B (対抗):**
  - Orchestration層（例: LangChain/LlamaIndex）を導入し、検索・回答フローの可観測性と差し替え性を上げる。
  - 反論: 学習コストと依存追加で短期速度が落ちる懸念あり。
- **Plan C (最速):**
  - 旧PoC（`care_rag_poc`）を一時運用しつつ、Plan B基盤を裏で整備して段階移行する。
  - 懸念: 二重運用の長期化で保守コストが増えるため、期限付き運用に限定すべき。

## 4. リソース想定
- **必要なAPIキー/権限:**
  - `GEMINI_API_KEY`（Gemini固定構成）
  - Docker実行権限（`docker compose up --build`）
  - PostgreSQL/Redis/MinIO へのローカル接続権限
  - `.env` 管理権限（Gemini APIキー設定）
- **不明点:**
  - 本番環境での正式な鍵管理方式（Secret Manager等）
  - 本命運用経路（旧実装継続か、現行基盤一本化か）の最終意思決定
