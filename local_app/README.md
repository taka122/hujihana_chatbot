# ふじはなチャットボット — ローカル版

Docker・PostgreSQL・Redis・MinIO **不要**で動作するスタンドアロン版チャットボットです。  
PDF・DOCX・TXT を取り込み、Gemini API を使って質問に回答します。

---

## 必要なもの

| 項目 | 内容 |
|---|---|
| Python | 3.11 以上 |
| Gemini API キー | [Google AI Studio](https://aistudio.google.com/app/apikey) から取得 |
| インターネット接続 | Gemini API への通信に必要 |

---

## セットアップ

```bash
# 1. リポジトリのルートで依存パッケージをインストール
pip install -r local_app/requirements.txt

# 2. (任意) API キーを環境変数にセット
export GEMINI_API_KEY=your_api_key_here

# 3. Streamlit アプリを起動
streamlit run local_app/app.py
```

ブラウザが自動で開き `http://localhost:8501` にアクセスします。

---

## 使い方

1. **サイドバーの「Gemini API キー」欄**に API キーを入力（環境変数で設定済みの場合は自動入力）
2. **「ドキュメントの追加」** で PDF / DOCX / TXT / MD をアップロード  
   → ✅ が表示されたら取り込み完了
3. **チャット欄**に質問を入力して Enter  
   → 回答と引用元が表示されます

---

## データの保存場所

| 種類 | パス |
|---|---|
| SQLite DB (チャンク・ベクトル) | `local_app/data/local.db` |
| アップロード済みファイル | `local_app/data/files/` |

---

## 注意事項

- Gemini API の利用には料金がかかります（[料金表](https://ai.google.dev/pricing)）
- ローカルの SQLite に全ベクトルを展開するため、文書数が数百件を超えると検索に時間がかかる場合があります
- OCR は Gemini Vision を使用するため、画像のみの PDF は追加コストが発生します
