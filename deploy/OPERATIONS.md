# 運用手順（ConoHa VPS / 藤花歯科クリニック chatbot）

本番デプロイ: `deploy@160.251.206.29` / `/opt/hujihana-chatbot`

公開エンドポイント（本番構成 = Mac main 設計）:
- **UI + API (nginx 経由、1 本化)**: http://160.251.206.29/
  - `/` → Next.js UI（未ログインは `/login` にリダイレクト）
  - `/login` → ログイン画面（パスワード認証）
  - `/api/auth/...` → Next.js のログイン/ログアウト API
  - `/api/chat` → Next.js 経由のチャット
  - `/api/backend/...` → Next.js 経由で FastAPI に転送
  - `/api/...`（上記以外） → FastAPI 直接
- **S3 (MinIO)**: http://160.251.206.29:9000 （プリサインドURL 発行用。公開）
- **MinIO Console**: 127.0.0.1:9001 （SSH トンネル経由のみ）
- **API (FastAPI)**: 127.0.0.1:8000 （VPS 内部のみ。外部には公開されていない）

認証:
- UI ログインパスワード: `.env` の `APP_LOGIN_PASSWORD`
- API 直接叩きパスワード: `.env` の `CLINIC_PASSWORD`（UI を通さないときのみ必要）

---

## 0. ログイン

```bash
# Mac から
ssh deploy@160.251.206.29
cd /opt/hujihana-chatbot
```

パスフレーズは Mac で `~/.ssh/id_ed25519` を作ったときのもの。

---

## 1. よく使うコマンド

すべて `cd /opt/hujihana-chatbot` してから実行。Docker プロジェクト名は `-p app` で固定（既存 volume 引き継ぎのため）。

```bash
# compose ファイルのエイリアス（毎回 -p / -f を書かない）
alias dc='sudo docker compose -p app -f docker-compose.prod.yml'

# 状態確認
dc ps

# 全ログ追尾
dc logs -f

# 個別ログ
dc logs -f api
dc logs -f worker
dc logs -f ui
dc logs -f nginx
dc logs --tail=100 postgres
dc logs --tail=100 minio

# 再起動（設定変更は無し）
dc restart api worker ui

# 全部停止（volume は残る）
dc down

# 全部起動（初回 or コード更新後）
dc up -d --build

# 1サービスだけ作り直す
dc up -d --force-recreate ui
```

---

## 2. コードを更新してデプロイし直す

Mac 側で（rsync で VPS の `/opt/hujihana-chatbot` に反映）：

```bash
cd /Users/manjyuuu/Downloads/fujihana-chatbot-main
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.next' \
  --exclude '.pytest_cache' --exclude 'worker.log' --exclude 'data' \
  --exclude '.env' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.DS_Store' --exclude '._*' \
  ./ deploy@160.251.206.29:/opt/hujihana-chatbot/
```

`.env` は意図的に除外している（VPS 側のシークレットを上書きしないため）。

VPS 側で：

```bash
cd /opt/hujihana-chatbot
sudo docker compose -p app -f docker-compose.prod.yml up -d --build
```

ビルドは 5〜10 分かかることがある（特に `next build`）。

---

## 3. DB マイグレーションを手動で実行

起動スクリプト (`scripts/start-api.sh`) が自動で `alembic upgrade head` を走らせるため通常は不要。
新しいマイグレーションを追加した後など、手動で流したい場合：

```bash
cd /opt/hujihana-chatbot
sudo docker compose -p app -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 4. バックアップ

### 4-1. Postgres をダンプ

```bash
cd /opt/hujihana-chatbot
sudo docker compose -p app -f docker-compose.prod.yml \
  exec -T postgres pg_dump -U postgres rag \
  > ~/backups/rag-$(date +%Y%m%d-%H%M%S).sql
```

初回のみ `mkdir -p ~/backups`。

### 4-2. Postgres リストア

```bash
cd /opt/hujihana-chatbot
cat ~/backups/rag-YYYYmmdd-HHMMSS.sql | \
  sudo docker compose -p app -f docker-compose.prod.yml \
  exec -T postgres psql -U postgres rag
```

### 4-3. MinIO（S3）のバケットバックアップ

ブラウザ / SSH トンネル経由で 9001 に入り、`rag-documents` を丸ごとダウンロードでも可。
CLI で取りたい場合：

```bash
# Mac から SSH トンネルで MinIO Console
ssh -L 9001:127.0.0.1:9001 -L 9000:127.0.0.1:9000 deploy@160.251.206.29
# 別ターミナルで
mc alias set vps http://localhost:9000 <S3_ACCESS_KEY> <S3_SECRET_KEY>
mc mirror --overwrite vps/rag-documents ~/backups/rag-documents-$(date +%Y%m%d)/
```

（`mc` が無ければ `brew install minio-mc`）

### 4-4. .env は必ずバックアップ

`/opt/hujihana-chatbot/.env` に POSTGRES / MinIO / CLINIC_PASSWORD / APP_LOGIN_PASSWORD / GEMINI_API_KEY が入っている。
一度だけでよいので手元に落として保管：

```bash
scp deploy@160.251.206.29:/opt/hujihana-chatbot/.env ~/secure/hujihana-chatbot.env
```

保管先は 1Password 等、暗号化された場所を推奨。

---

## 5. ログイン / SSH 鍵まわり

### 5-1. Mac から

```bash
ssh deploy@160.251.206.29
```

失敗する場合：
- Mac 側の `~/.ssh/id_ed25519` が存在するか
- VPS 側 `/home/deploy/.ssh/authorized_keys` に Mac のpubkey が入っているか
  （`ssh-keygen -y -f ~/.ssh/id_ed25519` の出力と一致するはず）

### 5-2. 鍵を追加する（新しい作業用PCから入りたい場合）

新PCで `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519` → `~/.ssh/id_ed25519.pub` を表示。
Mac から VPS に追加：

```bash
ssh deploy@160.251.206.29 'echo "<pubkey line>" >> ~/.ssh/authorized_keys'
```

### 5-3. rootでは入れない / パスワード認証は無効

セキュリティ対策で明示的に無効化済み:
- `/etc/ssh/sshd_config.d/01-hardening.conf`
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `PubkeyAuthentication yes`

戻したい（非推奨）場合は同ファイルを編集し `sudo systemctl restart ssh`。

---

## 6. GEMINI_API_KEY / ログインパスワードのローテーション

現在の `.env` に入っている Gemini キーはリポジトリにも含まれていたので、再発行を推奨。
ログインパスワードも適宜ローテーション可。

1. 新値を用意:
   - Gemini: Google AI Studio で新 API キー発行
   - UI: `openssl rand -hex 16` 等で新パスワード生成
2. VPS で `.env` を更新:
   ```bash
   sudo nano /opt/hujihana-chatbot/.env
   # GEMINI_API_KEY / APP_LOGIN_PASSWORD / CLINIC_PASSWORD を更新
   ```
3. 依存コンテナを再作成:
   ```bash
   cd /opt/hujihana-chatbot
   sudo docker compose -p app -f docker-compose.prod.yml up -d --force-recreate api worker ui
   ```
4. 動作確認（http://160.251.206.29 に再ログイン） → 旧キーを無効化

---

## 7. トラブルシュート

### 7-1. http://160.251.206.29 が開かない / 502

```bash
dc ps
# すべて Up / healthy になっているか？

dc logs --tail=100 nginx
dc logs --tail=100 ui
dc logs --tail=100 api
```

よくある原因:
- `app-api-1` が `Restarting` → `dc logs api` で alembic エラー等
- `app-ui-1` で `HOSTNAME` が container ID になっている
  → `docker-compose.prod.yml` の ui サービスに `HOSTNAME: 0.0.0.0` があるか確認
- nginx upstream の ui or api が起動前 → `depends_on` 順序を確認

### 7-2. `/api/backend/...` が 502 で `fetch failed`

`nginx/default.conf` の `/api/backend/` ブロックに `proxy_set_header Upgrade` / `Connection "upgrade"` が
あると Node の fetch が失敗する。**それらの 2 行は /api/backend/ には置かないこと**。
`/api/auth/`, `/api/chat`, `/` の WebSocket 用には残して良い。

修正したら:
```bash
sudo docker exec app-nginx-1 nginx -s reload
```

### 7-3. ログインできない / Cookie が保存されない

- `AUTH_COOKIE_SECURE=false` が `.env` にあるか確認
  （HTTPS 化したら `true` に変える）
- `APP_LOGIN_PASSWORD` が `.env` に設定されているか

### 7-4. アップロードができない / ファイルが消える

- MinIO が起動しているか: `curl http://localhost:9000/minio/health/live` → 200
- `.env` の `S3_ACCESS_KEY` と MinIO 側 `MINIO_ROOT_USER` が一致しているか
- ブラウザから出る S3 プリサインドURLが `http://160.251.206.29:9000` で始まっているか
  → ならないなら `S3_PUBLIC_ENDPOINT` を見直す

### 7-5. OOM killed / ビルドが失敗

1GB RAM は余裕がないので、swap を確認:

```bash
free -h
swapon --show
```

4GB swap が無ければ（本デプロイでは作成済み）:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && \
  sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 7-6. 外部アクセスできない (80/9000)

順番に切り分け:

```bash
# 1. VPS内では応答する？
curl -I http://localhost/

# 2. UFW 許可されている？
sudo ufw status
# → 80/tcp, 9000/tcp が ALLOW になっているはず

# 3. ConoHa コントロールパネル側のセキュリティグループも確認
#    → 80 (HTTP), 9000 が許可されているか
```

### 7-7. ディスクが埋まった

```bash
df -h
sudo docker system df
sudo docker system prune -a -f   # 使っていないイメージ削除
```

**注意**: `docker volume` は削除しないこと（postgres / minio のデータが消える）。

---

## 8. リソース / ヘルスチェック常時監視

```bash
# コンテナのCPU/MEM
sudo docker stats --no-stream

# ディスク
df -h

# システム負荷
top -b -n 1 | head -20
```

---

## 9. 完全停止 / 完全リセット

一時的に止めるだけ:

```bash
cd /opt/hujihana-chatbot
sudo docker compose -p app -f docker-compose.prod.yml down
```

**警告**: 以下はデータが完全に消えます。本番では使わない。

```bash
# ボリュームごと消す（postgres / minio が空になる）
sudo docker compose -p app -f docker-compose.prod.yml down -v
```

---

## 10. HTTPS 化（次の TODO）

現在は http のみ。以下で HTTPS 化できる。

1. ドメインを VPS に向ける（A レコード）
2. Certbot を VPS に入れる:
   ```bash
   sudo apt install certbot
   # nginx コンテナは compose で動いているので webroot または standalone で取得
   ```
3. 証明書を `nginx/` 配下にマウントし、`nginx/default.conf` を 443 対応に
4. `.env` の `AUTH_COOKIE_SECURE=true` に変更して UI を再起動

---

## 11. 付録: 変更履歴

- 2026-04-18 (朝): 初回デプロイ（develop ブランチ、シンプル構成）
  - Ubuntu 24.04 / 1GB RAM + 4GB swap
  - deploy ユーザー、SSH 公開鍵認証化、PasswordAuthentication 無効化
  - Docker Engine 29.4 + Compose v5.1
  - UFW: 22/3000/8000/9000 を許可
- 2026-04-18 (昼): **main ブランチの本来設計に作り直し**
  - `/opt/app` → `/opt/hujihana-chatbot`（個人ファイルと混在を避けるため）
  - `docker-compose.yml` + `deploy/docker-compose.prod.yml` 2 ファイル構成 → `docker-compose.prod.yml` 単独
  - frontend サービス → ui サービス（Next.js standalone ビルド）
  - nginx コンテナ追加、80 番で UI/API を 1 本化
  - 認証追加: `CLINIC_PASSWORD`, `APP_LOGIN_PASSWORD`
  - UFW 3000/8000 削除、80 のみ公開（API は 127.0.0.1 内部のみ）
  - 既存 docker volume (`app_postgres_data`, `app_minio_data`) は `-p app` で引き継ぎ
