from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "documents"
STORAGE_DIR = ROOT_DIR / "storage"
DB_PATH = STORAGE_DIR / "rag.db"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K = 3

