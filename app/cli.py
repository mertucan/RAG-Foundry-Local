from __future__ import annotations

import argparse

from .chat_engine import ChatEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the local RAG assistant from the terminal.")
    parser.add_argument("--compact", action="store_true", help="Use compact mode for faster, shorter answers.")
    args = parser.parse_args()

    print("=== Gas Field RAG CLI ===")
    print("Loading Foundry Local models. This may take a moment on first run.\n")

    engine = ChatEngine()
    try:
        engine.init()
        engine.set_compact_mode(args.compact)
        print("\nReady. Type a question, or type 'exit' to quit.\n")

        history: list[dict] = []
        while True:
            question = input("You> ").strip()
            if question.lower() in {"exit", "quit", "q"}:
                break
            if not question:
                continue

            result = engine.query(question, history[-6:])
            answer = result["text"]
            print(f"\nAssistant>\n{answer}\n")

            sources = result.get("sources", [])
            if sources:
                print("Sources:")
                for source in sources:
                    score = int(float(source["score"]) * 100)
                    chunk = source.get("chunkIndex", 0)
                    print(f"- {source['title']} [{source['docId']} #{chunk}] {score}%")
                print()

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
    finally:
        engine.close()


if __name__ == "__main__":
    main()
