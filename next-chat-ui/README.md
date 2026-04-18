# next-chat-ui

Gemini RAGのチャットUIを表示する Next.js アプリです。

## 起動

```bash
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開いてください。

Docker で起動する場合:

```bash
cd ..
cp .env.example .env
docker compose --profile frontend up --build
```

この場合もブラウザは `http://localhost:3000` です。バックエンド API への接続先は `API_PROXY_TARGET=http://api:8000` が自動で設定されます。

## 環境変数

- `API_PROXY_TARGET`（推奨）: Next の同一オリジン API プロキシが中継するバックエンド URL。未設定時は `http://localhost:8000` を利用します。
- `CLINIC_PASSWORD` または `LOGIN_PASSWORD`: ログインを有効化する共通パスワード。未設定ならフロントのログイン画面は必須になりません。
- `FACILITIES_CSV_PATH`（任意）: `/api/chat` が参照する施設CSVのパス。未設定時は `./data/facilities_sample.csv` と `../data/facilities_sample.csv` を順に探します。

ブラウザは常に Next の `/api/backend/*` にアクセスし、Next サーバーがバックエンドへ中継します。`localhost` / `127.0.0.1` / HTTPS 差異による CORS や mixed content を避けるためです。

## 本番ビルド

```bash
npm run build
```

Dockerで本番起動する場合は同梱の `Dockerfile` を使えます。

## Geminiキーの上書き設定

- 画面左下の設定ボタン（歯車）から任意で `Gemini API Key` を保存可能
- 保存値は `X-GEMINI-API-Key` ヘッダで送信されます

入力値はブラウザのローカルストレージに保存され、リクエストヘッダに付与されます。
