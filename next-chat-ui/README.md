# next-chat-ui

Gemini RAGのチャットUIを表示する Next.js アプリです。

## 起動

```bash
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開いてください。

## 環境変数

- `API_PROXY_TARGET`（推奨）: Next の同一オリジン API プロキシが中継するバックエンド URL。未設定時は `http://localhost:8000` を利用します。
- `NEXT_PUBLIC_API_BASE_URL`（任意）: 互換用。`API_PROXY_TARGET` 未設定時のフォールバックとしてのみ使います。

ブラウザは常に Next の `/api/backend/*` にアクセスし、Next サーバーがバックエンドへ中継します。`localhost` / `127.0.0.1` / HTTPS 差異による CORS や mixed content を避けるためです。

## Geminiキーの上書き設定

- 画面左下の設定ボタン（歯車）から任意で `Gemini API Key` を保存可能
- 保存値は `X-GEMINI-API-Key` ヘッダで送信されます

入力値はブラウザのローカルストレージに保存され、リクエストヘッダに付与されます。
