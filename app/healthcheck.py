from __future__ import annotations

from app.config import DB_PATH
from app.db import connect, count_chunks, init_db


def main() -> None:
    print("RAG Foundry Local healthcheck")
    print("============================")

    conn = connect(DB_PATH)
    init_db(conn)
    print(f"SQLite DB: {DB_PATH}")
    print(f"Chunk count: {count_chunks(conn)}")

    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager  # type: ignore

        config = Configuration(app_name="rag_foundry_local_healthcheck")
        FoundryLocalManager.initialize(config)
        manager = FoundryLocalManager.instance
        models = manager.catalog.list_models()
        print("Foundry Local SDK: OK")
        print(f"Available models: {len(models)}")
        for model in models[:10]:
            alias = getattr(model, "alias", None) or getattr(model, "id", "unknown")
            print(f"- {alias}")
    except Exception as exc:
        print("Foundry Local SDK: NOT READY")
        print(f"Reason: {exc}")


if __name__ == "__main__":
    main()
