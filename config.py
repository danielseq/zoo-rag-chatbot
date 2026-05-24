from dotenv import load_dotenv
import os

# Models
OLLAMA_MODEL = "llama3:latest"
EMBED_MODEL = "nomic-embed-text"

# Paths
DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"

# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Retrieval
TOP_K = 4

# IUCN
IUCN_API_KEY = os.getenv("IUCN_API_KEY")
IUCN_BASE_URL = "https://api.iucnredlist.org/api/v3"