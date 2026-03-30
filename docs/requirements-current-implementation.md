# 現行実装ベース 要件定義まとめ

最終更新日: 2026-02-19  
ステータス: 実装突合済み（ドラフト）

## 1. 要件ソースの棚卸し
| 区分 | ファイル | 役割 | 信頼度 |
|---|---|---|---|
| 事業/上位要件 | `/Users/manjyuuu/care-rag-chat/docs/requirements-definition.md` | 背景・目的・機能/非機能・リスクを定義する親文書 | 中（仮説/不明が多い） |
| 実装スコープ | `/Users/manjyuuu/care-rag-chat/README.md` | MVP範囲、API、運用前提を定義 | 高（現実装に近い） |
| 検証要件 | `/Users/manjyuuu/care-rag-chat/docs/poc-validation-plan.md` | KPI/撤退ライン/検証アプローチ定義 | 中（閾値は仮説） |
| 実験ログ/差分 | `/Users/manjyuuu/care-rag-chat/docs/poc-experiment-note.md` | 実装差分、既知課題、次アクション | 高（差分把握に有効） |

## 2. 現行実装で成立している要件（事実ベース）
1. Workspace分離
   - APIクエリは `workspace_id` で絞り込み。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/routers/documents.py:34`, `/Users/manjyuuu/care-rag-chat/app/routers/chat.py:58`
2. 非同期取り込みパイプライン
   - アップロード後にキュー投入し、workerで ingest を実行。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/routers/documents.py:80`, `/Users/manjyuuu/care-rag-chat/worker/jobs.py:1`
3. 対応ファイル形式（実装上）
   - 取り込み対応: `pdf/docx/txt/md`。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/services/ingest.py:66`, `/Users/manjyuuu/care-rag-chat/app/services/ingest.py:72`, `/Users/manjyuuu/care-rag-chat/app/services/ingest.py:78`
4. 非対応形式の明示エラー
   - `ppt/pptx`, `xls/xlsx`, 画像系はMVP非対応として失敗扱い。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/services/ingest.py:85`
5. 回答ガードレール
   - 失敗時/根拠不足時に「見つからない」系へフォールバック。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/routers/chat.py:63`, `/Users/manjyuuu/care-rag-chat/app/routers/chat.py:71`
6. 根拠提示のためのAPI
   - `ingestion-report`, `chunk`, `presigned-url`, `chat/query` を提供。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/app/routers/documents.py:116`, `/Users/manjyuuu/care-rag-chat/app/routers/documents.py:151`, `/Users/manjyuuu/care-rag-chat/app/routers/chat.py:23`
7. インフラ前提
   - PostgreSQL/Redis/MinIO を Docker Compose で起動する構成。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/docker-compose.yml:2`

## 3. 要件と実装の不整合・未達
1. UI受け入れ拡張子とバックエンド対応範囲の不一致
   - UIは `pptx/xlsx/png/jpg` を許可するが、バックエンドはMVP非対応。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/next-chat-ui/components/doc-uploader.tsx:20`, `/Users/manjyuuu/care-rag-chat/app/services/ingest.py:85`
2. `preview` APIの契約不一致
   - UIは `/preview` を呼ぶが、404時に `/presigned-url` へフォールバック。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/next-chat-ui/lib/api/client.ts:316`, `/Users/manjyuuu/care-rag-chat/next-chat-ui/lib/api/client.ts:322`, `/Users/manjyuuu/care-rag-chat/app/routers/documents.py:135`
3. 旧実装と現行実装の二重系統
   - `next-chat-ui/app/api/chat/route.ts`（旧）と `app/routers/chat.py`（現行）が共存。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/next-chat-ui/app/api/chat/route.ts:1`, `/Users/manjyuuu/care-rag-chat/app/routers/chat.py:1`
4. テスト対象の偏り
   - `care_rag_poc` 中心のテストが多く、`app/routers/* + worker/*` の統合E2Eは不足。  
   - 根拠: `/Users/manjyuuu/care-rag-chat/tests/test_chat_engine.py:3`, `/Users/manjyuuu/care-rag-chat/tests/test_rag_responder.py:3`

## 4. 非機能要件の充足状況（現時点）
| 項目 | 状態 | 根拠/備考 |
|---|---|---|
| 性能目標（p95 8秒） | 未検証 | KPI記載はあるが定常計測実装は不明 |
| 可用性目標（99.0%） | 未検証 | ローカルPoC中心でSLO運用は未整備 |
| セキュリティ（ログ保持方針） | 不明 | 保存有無・保持期間の方針は未確定 |
| 監視（失敗率/ヒット率） | 部分対応 | 失敗ログはあるがKPI監視体系は未確立 |

## 5. 現実装ベースの確定要件（暫定）
1. Must
   - Workspace単位でのデータ分離
   - `pdf/docx/txt/md` の非同期取り込み
   - 根拠付き回答、根拠不足時の断定回避
   - 取り込みレポートと原本参照URLの提供
2. Should
   - UIとバックエンドの対応フォーマット統一
   - `preview` 契約を一本化（実装 or 廃止）
   - `upload -> ingest -> query` の統合E2EをCIへ追加
3. Won't（現MVP）
   - `pptx/xlsx/画像` の本取り込み対応
   - 空き状況リアルタイム照会、予約代行

## 6. 反論・代替案・懸念点（更新版）
1. 反論
   - 先に機能追加を進めるより、契約不一致（拡張子/preview）の解消を優先しないと失敗率が下がらない。
2. 代替案
   - 代替案A: UI受け入れを `pdf/docx/txt/md` に制限し、サーバ仕様に即時一致させる。
   - 代替案B: サーバ側で `pptx/xlsx/画像` の段階対応ロードマップを定義し、UIに「ベータ対応」を明示する。
3. 懸念点
   - 旧/新ルートの並存が続くと、障害対応と運用判断コストが継続的に増える。
   - KPI閾値は文書上にあるが、計測系未整備のままでは達成判定ができない。

## 7. 不明点（判断保留）
1. 本番での秘密情報管理方式（Secret Manager等）は不明。
2. 相談テキストの保存有無/保持期間は不明。
3. 旧実装の廃止期限と移行方針は不明。

