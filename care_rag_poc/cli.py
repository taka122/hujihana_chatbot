import argparse
import os

from care_rag_poc.chat_engine import CareRagChatEngine
from care_rag_poc.dataset import load_facilities
from care_rag_poc.rag import GeminiApiError, build_gemini_rag_responder
from care_rag_poc.retriever import FacilityRetriever


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Care RAG Chat PoC")
    parser.add_argument(
        "--data",
        default="data/facilities_sample.csv",
        help="Path to facility CSV",
    )
    parser.add_argument(
        "--top-k",
        default=3,
        type=int,
        help="Number of candidates to return",
    )
    parser.add_argument(
        "--backend",
        choices=["rag", "rule"],
        default="rag",
        help="Answer backend: rag (Gemini) or rule (LLMなし)",
    )
    parser.add_argument(
        "--gemini-api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API key (or GEMINI_API_KEY env)",
    )
    parser.add_argument(
        "--gemini-model",
        default=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        help="Gemini generation model",
    )
    parser.add_argument(
        "--gemini-embedding-model",
        default=os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        help="Gemini embedding model",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    facilities = load_facilities(args.data)
    retriever = FacilityRetriever(facilities)
    rag_responder = None
    if args.backend == "rag":
        if not args.gemini_api_key:
            raise SystemExit(
                "RAG backendにはGemini APIキーが必要です。"
                " GEMINI_API_KEYを設定するか --gemini-api-key を指定してください。"
            )
        try:
            rag_responder = build_gemini_rag_responder(
                facilities=facilities,
                api_key=args.gemini_api_key,
                generation_model=args.gemini_model,
                embedding_model=args.gemini_embedding_model,
            )
        except GeminiApiError as exc:
            raise SystemExit(f"Gemini初期化に失敗しました: {exc}") from exc

    engine = CareRagChatEngine(retriever, rag_responder=rag_responder)

    print(
        "介護事業所チャットPoCを開始します。"
        f"backend={args.backend}。終了は `exit`/`quit`、条件リセットは `/reset`。"
    )
    while True:
        user_input = input("\n相談内容> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("終了します。")
            break
        if user_input == "/reset":
            engine.reset_context()
            print("会話コンテキストをリセットしました。")
            continue
        if not user_input:
            continue

        try:
            result = engine.ask(user_input, top_k=args.top_k)
        except GeminiApiError as exc:
            print(f"\nGemini呼び出しに失敗しました: {exc}")
            continue
        print("\n" + result.text)


if __name__ == "__main__":
    main()
