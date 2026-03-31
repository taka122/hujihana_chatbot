"""Streamlit UI for the local standalone chatbot app.

Run from the repository root:

    streamlit run local_app/app.py

Or, if the current directory is local_app/:

    streamlit run app.py

Requires GEMINI_API_KEY to be provided in the sidebar or as an
environment variable.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import streamlit as st

# Shim must be installed before any app.* imports.
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import local_app._shim  # noqa: F401

from app.services.answer import AnswerService
from local_app.local_db import LocalDatabase
from local_app.local_ingest import ingest_document
from local_app.local_retrieve import local_hybrid_retrieve

logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ふじはなチャットボット",
    page_icon="🌸",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------
_DATA_DIR = _repo_root / "local_app" / "data"
_DB_PATH = _DATA_DIR / "local.db"
_FILES_DIR = _DATA_DIR / "files"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_FILES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Shared DB (cached per session)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_db() -> LocalDatabase:
    return LocalDatabase(_DB_PATH)


db = get_db()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": "user"|"assistant", "content": str, "citations": list}
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🌸 ふじはなチャットボット")
    st.caption("ローカル版 — Docker 不要")

    st.divider()

    # API key
    api_key_input = st.text_input(
        "Gemini API キー",
        value=st.session_state.api_key,
        type="password",
        help="Google AI Studio から取得した API キーを入力してください。",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.divider()

    # Upload
    st.subheader("📂 ドキュメントの追加")
    uploaded = st.file_uploader(
        "PDF / DOCX / TXT / MD",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )

    if uploaded and st.session_state.api_key:
        for uf in uploaded:
            with st.spinner(f"取り込み中: {uf.name} …"):
                try:
                    ingest_document(
                        file_name=uf.name,
                        mime_type=uf.type or "application/octet-stream",
                        data=uf.read(),
                        gemini_api_key=st.session_state.api_key,
                        db=db,
                        save_dir=_FILES_DIR,
                    )
                    st.success(f"✅ {uf.name} を取り込みました")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {uf.name}: {exc}")
    elif uploaded and not st.session_state.api_key:
        st.warning("Gemini API キーを先に入力してください。")

    st.divider()

    # Document list
    st.subheader("📋 ドキュメント一覧")
    docs = db.list_documents()
    if not docs:
        st.caption("まだドキュメントがありません。")
    else:
        for doc in docs:
            status = doc["status"]
            icon = {"ready": "✅", "processing": "⏳", "failed": "❌"}.get(status, "❓")
            col1, col2 = st.columns([4, 1])
            col1.caption(f"{icon} {doc['file_name']}")
            if col2.button("🗑️", key=f"del_{doc['id']}", help="削除"):
                db.delete_document(doc["id"])
                st.rerun()

    st.divider()

    if st.button("💬 会話をリセット"):
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# Main — Chat
# ---------------------------------------------------------------------------
st.title("💬 チャット")

# Show chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for cite in msg.get("citations", []):
            st.caption(
                f"📄 {cite['file_name']}  {cite['ref']}  "
                f"（スコア: {cite['score']:.2f}）"
            )
            with st.expander("スニペット", expanded=False):
                st.text(cite["snippet"])

# Chat input
query = st.chat_input("質問を入力してください…")

if query:
    if not st.session_state.api_key:
        st.error("サイドバーに Gemini API キーを入力してください。")
        st.stop()

    ready_docs = [d for d in db.list_documents() if d["status"] == "ready"]
    if not ready_docs:
        st.warning("ドキュメントをアップロードして取り込みを完了させてください。")
        st.stop()

    # Show user message
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.chat_history.append({"role": "user", "content": query, "citations": []})

    # Retrieve and answer
    with st.chat_message("assistant"):
        with st.spinner("検索・回答生成中…"):
            try:
                # Set API key env var for app.config readers
                os.environ["GEMINI_API_KEY"] = st.session_state.api_key

                retrieved = local_hybrid_retrieve(
                    db=db,
                    query=query,
                    gemini_api_key=st.session_state.api_key,
                )

                answer_service = AnswerService(gemini_api_key=st.session_state.api_key)
                result = answer_service.answer(
                    query=query,
                    contexts=retrieved,
                    min_score=0.25,
                )

                answer = result.answer
                citations_raw = result.citations

            except Exception as exc:  # noqa: BLE001
                st.error(f"エラーが発生しました: {exc}")
                st.stop()

        # Format answer
        conclusion = answer.get("conclusion", "")
        details = answer.get("details", "")
        notes = answer.get("notes", "")
        next_actions: list[str] = answer.get("next_actions", [])

        md_parts = []
        if conclusion:
            md_parts.append(f"**{conclusion}**")
        if details:
            md_parts.append(details)
        if notes:
            md_parts.append(f"*{notes}*")
        if next_actions:
            md_parts.append("**次のアクション:**")
            for action in next_actions:
                md_parts.append(f"- {action}")

        answer_md = "\n\n".join(md_parts)
        st.markdown(answer_md)

        # Build citations for display
        display_citations = []
        for cite in citations_raw:
            display_citations.append(
                {
                    "file_name": cite.get("file_name", ""),
                    "ref": cite.get("ref", ""),
                    "snippet": cite.get("snippet", ""),
                    "score": cite.get("score") or 0.0,
                }
            )
            st.caption(
                f"📄 {cite.get('file_name', '')}  {cite.get('ref', '')}  "
                f"（スコア: {(cite.get('score') or 0.0):.2f}）"
            )
            with st.expander("スニペット", expanded=False):
                st.text(cite.get("snippet", ""))

    st.session_state.chat_history.append(
        {"role": "assistant", "content": answer_md, "citations": display_citations}
    )
