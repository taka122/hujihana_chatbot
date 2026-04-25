# ConoHa VPS デプロイ手順

このドキュメントは `hujihana_chatbot` を ConoHa VPS（Ubuntu 22.04 / 24.04, 1GB RAM, IP `160.251.206.29`）に
docker compose で本番デプロイする手順です。順番にコピペで進められるように書いてあります。

構成：

```
ブラウザ ──▶ http://160.251.206.29:3000   (Next.js: next-chat-ui)
                       │
                       │ /api/backend/* をサーバ側プロキシ
                       ▼
                http://api:8000          (FastAPI)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   postgres+pgvector  redis        minio (S3互換)
```

ワーカー（`rag-worker`）も同じネットワーク上で動きます。

---

## 0. 事前準備（手元のPC）

ConoHaコントロールパネルにログインして、次の3つを確認・設定してください。

### 0-1. セキュリティグループを開ける

VPS設定 → ネットワーク情報 → セキュリティグループの「編集」から、最低限以下を有効にしてください：

- **IPv4v6-SSH**（22番ポート）— 必須
- **IPv4v6-Web**（80/443番ポート）— 念のため
- 加えて、コントロールパネル上で次のカスタムポートを開ける必要があります：
  - **3000/tcp**（Next.js フロントエンド）
  - **8000/tcp**（FastAPI を直接叩くため。最終的に閉じてもOK）
  - **9000/tcp**（MinIO の S3 API。プリサインドURLでファイルダウンロードに使う）

ConoHaの標準セキュリティグループに 3000/8000/9000 のテンプレが無い場合は、
「default」を選んだ上でVPS内のufwで開ければ十分です（`bootstrap.sh` がやります）。

### 0-2. rootパスワードでSSHできるようにする

ConoHaのVPSは初期状態では rootパスワードでのSSHが**無効**になっていることがあります。
コントロールパネルの「コンソール」から一度ログインして、次を実行してください：

```bash
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh
```

> 💡 余裕があれば、後述の「セキュリティを締める」セクションに従って公開鍵認証に切り替えてください。

### 0-3. 手元から接続できるか確認

手元のターミナル（macOSなら標準のTerminal.app）で：

```bash
ssh root@160.251.206.29
```

Yes/no を聞かれたら `yes`、そのあと ConoHa で設定したrootパスワードを入力。プロンプトが
`root@xxxxx:~#` になればOKです。

---

## 1. プロジェクトをVPSに送る

手元のPCで、プロジェクトのルートディレクトリ（`hujihana_chatbot-main` の中）に移動して：

```bash
# 手元の.envは秘密情報なので一旦別名にする（後でscpする）
cd /path/to/hujihana_chatbot-main

# 不要な大物を除いてrsyncで送る（worker.log や node_modules を除外）
rsync -avz \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '.pytest_cache' \
  --exclude 'worker.log' \
  --exclude 'data' \
  ./ root@160.251.206.29:/opt/hujihana_chatbot/
```

`rsync` が無い場合は `scp -r` でもOKですが、`node_modules` を除外しないと
何百MBも送ることになるので注意。

---

## 2. VPS上でブートストラップ

ssh して、Docker やスワップなどを一括で入れます：

```bash
ssh root@160.251.206.29
cd /opt/hujihana_chatbot
bash deploy/bootstrap.sh
```

完了すると `docker --version` と `docker compose version` が出ます。
（5〜10分程度）

---

## 3. 本番用 .env を作る

まだ .env がVPS上に無ければ、テンプレートからコピーします：

```bash
cd /opt/hujihana_chatbot
cp deploy/.env.production.example .env
nano .env
```

最低限編集すべき項目：

| 変数 | 何を入れるか |
|---|---|
| `POSTGRES_PASSWORD` | 推測されにくい長めのパスワード |
| `DATABASE_URL` | 上のパスワードを反映（postgres:**ここ**@postgres:5432/rag） |
| `MINIO_ROOT_PASSWORD` / `S3_SECRET_KEY` | 推測されにくいもの |
| `GEMINI_API_KEY` | 既存の `.env` に入っていたキーをそのまま貼り付け |
| `S3_PUBLIC_ENDPOINT` | `http://160.251.206.29:9000` のまま |
| `CORS_ORIGINS` | `http://160.251.206.29:3000,http://160.251.206.29` |

> ⚠️ 既存の `.env` に書かれている `GEMINI_API_KEY` は、コードリポジトリにそのまま入っているため
> 本来は **ローテート（再発行）** することを強くおすすめします。Google AI Studio の
> 「APIキーを再生成」から新しいキーを取得し、そちらを貼ってください。

---

## 4. 立ち上げる

```bash
cd /opt/hujihana_chatbot
bash deploy/up.sh
```

初回は Docker のビルドに 5〜10 分かかります（`pgvector` イメージのpull、`pip install`、
`npm ci` & `next build`）。

完了すると `docker compose ps` の一覧が表示されます。
すべての行が `Up` または `running` になっていれば成功です。

---

## 5. 動作確認

手元のPC（またはVPS上）から：

```bash
# API ヘルスチェック
curl -i http://160.251.206.29:8000/health

# フロントエンド
curl -I http://160.251.206.29:3000
```

ブラウザで `http://160.251.206.29:3000` を開くと next-chat-ui が表示されます。

---

## 6. よく使う運用コマンド

すべて `cd /opt/hujihana_chatbot` で実行してください。

```bash
# サービスの状態
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml ps

# ログ（API）
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml logs -f api

# ログ（worker）
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml logs -f worker

# 全部止める
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml down

# 全部止めて再起動（コードを更新したあと）
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build

# DBマイグレーションを手動で走らせる
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml exec api alembic upgrade head
```

---

## 7. つまずきやすいポイント

### 7-1. ビルド中に out of memory で死ぬ

`next build` か `pip install` のどちらかでメモリが足りないことがあります。
`bootstrap.sh` で 2GB swap を作っているはずですが、念のため：

```bash
free -h
swapon --show
```

スワップが無ければ：

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 7-2. ブラウザからアクセスできない

順番に切り分け：

```bash
# 1) VPS内ではアクセスできる？
curl -I http://localhost:3000

# 2) ufw は許可している？
ufw status

# 3) ConoHa 側のセキュリティグループで 3000/8000/9000 が空いてる？
#    → ConoHa コントロールパネルで確認
```

### 7-3. `alembic upgrade head` が永遠に待つ

postgres の起動より先に api が走り始めると `start-api.sh` がリトライし続けます。
`docker compose logs postgres` で「ready to accept connections」が出ていればOK。

### 7-4. MinIO のデータが消えた

`docker compose down -v` を実行するとボリュームごと消えます。`-v` は付けないこと。

---

## 8. セキュリティを締める（任意・推奨）

最低限やっておきたいこと：

1. **公開鍵認証に切り替えてパスワードログインを無効化**
   ```bash
   # 手元から
   ssh-copy-id root@160.251.206.29
   # VPS上で
   sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
   systemctl restart ssh
   ```

2. **rootではなく作業用ユーザを作る**
   ```bash
   adduser deploy
   usermod -aG sudo,docker deploy
   ```

3. **fail2ban を入れて総当たりを止める**
   ```bash
   apt-get install -y fail2ban
   systemctl enable --now fail2ban
   ```

4. **8000 ポートを閉じる**（フロントエンド経由でしか触らせない場合）
   ```bash
   ufw delete allow 8000/tcp
   ```
   ConoHa側のセキュリティグループも忘れずに。

5. **MinIO のコンソール（9001）はSSHトンネル越しでしか触らない**
   ```bash
   ssh -L 9001:localhost:9001 root@160.251.206.29
   # 手元で http://localhost:9001
   ```

---

## 9. 後片付け / アップデート

コードを直したら手元から rsync で送り直して、VPSで再ビルド：

```bash
# 手元
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.next' \
  --exclude '.pytest_cache' --exclude 'worker.log' --exclude 'data' \
  ./ root@160.251.206.29:/opt/hujihana_chatbot/

# VPS
cd /opt/hujihana_chatbot
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build
```

おわり。
