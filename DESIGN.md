# DESIGN.md — Zoo & Conservation RAG Chatbot

## Overview

This project is a Retrieval-Augmented Generation (RAG) chatbot designed for zoo and wildlife conservation contexts. It allows users to query a curated library of species and conservation documentation using natural language, receiving accurate, grounded answers sourced directly from the document library rather than relying solely on a language model's parametric knowledge.

The system runs entirely locally using Ollama, with no external API dependencies beyond the initial document fetch.

---

## Architecture

```
User Query
    │
    ▼
[ chat.py — CLI Interface ]
    │
    ├──► Embed query with nomic-embed-text (via Ollama)
    │
    ├──► Query ChromaDB for top-K similar chunks
    │
    ├──► Inject retrieved chunks + conversation history into prompt
    │
    └──► Generate answer with llama3 (via Ollama)
            │
            ▼
    Streamed Answer + Source Citations → User
```

### Components

| Component | Tool | Role |
|---|---|---|
| Document Source | Wikipedia API (`wikipedia-api`) | Fetches species articles as markdown |
| Chunking | Plain Python | Paragraph-aware splitting with hard fallback |
| Embeddings | `nomic-embed-text` via Ollama | Converts text to vector representations |
| Vector Store | ChromaDB (persistent) | Stores and retrieves chunks by similarity |
| LLM | `llama3:latest` via Ollama | Generates answers from retrieved context |
| Interface | Python CLI | Streaming conversational loop with history |

All components run entirely on-device. No data leaves the machine.

---

## Data Strategy

### Source Selection

Species articles are fetched from Wikipedia using the `wikipedia-api` Python library. Wikipedia was chosen over alternatives for the following reasons:

- **Reliability** — clean REST API, no scraping fragility or bot protection issues
- **Content richness** — articles contain detailed narrative text covering taxonomy, habitat, diet, behaviour, threats, and conservation status — ideal for RAG
- **No authentication** — no API keys or rate limiting concerns
- **Credibility** — Wikipedia conservation articles are well-maintained and widely cited

The initial target source was the IUCN Red List API (the authoritative global standard for conservation status data), but access was blocked by Cloudflare bot protection on v3 and required a separate registration process for v4. Wikipedia provides comparable narrative depth with significantly better programmatic accessibility. For a production system, a combination of both — IUCN for structured status data and Wikipedia for narrative context — would be ideal.

The document library covers 15 species of conservation significance:

- African Elephant, Tiger, Mountain Gorilla, Giant Panda, Amur Leopard
- Black Rhinoceros, Green Sea Turtle, Snow Leopard, Vaquita, African Penguin
- West Indian Manatee, Polar Bear, Chimpanzee, Whale Shark, Sumatran Orangutan

Each article is saved as a markdown file in `docs/` and ranges from ~75 to ~190 lines of content.

### Chunking Strategy

Documents are split using a custom paragraph-aware chunker with the following configuration:

```python
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 50     # overlap between chunks
```

The chunker works in two passes:

1. **Paragraph split** — text is first divided on double newlines (`\n\n`), keeping semantically related sentences together
2. **Hard split fallback** — any paragraph exceeding `CHUNK_SIZE` is further split by character count with overlap, ensuring no chunk exceeds the size limit

**Why these settings:**

- **Chunk size of 500** — balances specificity (small enough to retrieve a precise fact) with context (large enough to be coherent). Too large and retrieval becomes noisy; too small and chunks lose meaning.
- **Overlap of 50** — prevents facts that span chunk boundaries from being lost. A sentence split across two chunks will appear in both.
- **Paragraph-first approach** — keeps semantically related content together wherever possible, producing more coherent chunks than pure character splitting.

A 500-character chunk is approximately 80–120 words, roughly one or two paragraphs of natural prose — a natural unit for a single factual claim or description.

LangChain was deliberately excluded from the final implementation. An earlier version used `RecursiveCharacterTextSplitter` and `DirectoryLoader`, but these were replaced with plain Python to reduce dependencies and make the chunking logic fully transparent and controllable.

### Embeddings

Text is embedded using `nomic-embed-text`, a high-quality open embedding model served locally through Ollama. Each chunk and each user query is embedded into the same vector space, enabling semantic similarity search.

`nomic-embed-text` was chosen because:
- It is purpose-built for retrieval tasks
- It runs efficiently on Apple Silicon via Ollama
- It pairs naturally with the rest of the local Ollama stack
- Using the same model at ingest and query time is essential — mismatched embedding models produce meaningless similarity scores

### Vector Storage

Embeddings are stored in **ChromaDB**, a lightweight vector database that runs in-process and persists to disk. ChromaDB was chosen for:

- **Zero configuration** — no server to run, no Docker required
- **Persistent storage** — the `chroma_db/` directory survives between sessions; ingest runs once
- **Python-native** — integrates directly without an additional service layer

The collection is named `zoo_docs`. On each ingest run the collection is deleted and rebuilt from scratch, ensuring the database always reflects the current state of `docs/`.

---

## Prompt Engineering

### System Framing

The LLM is given a strict grounding instruction via a system message:

```
You are a zoo and wildlife conservation assistant with access to a specific document library.
Answer questions ONLY using the context provided below.
Do NOT use any outside knowledge or training data.
If the answer cannot be found in the context, say exactly:
"I don't have that information in my knowledge base."
Never make up species, statistics, or facts not present in the context.
If you are unsure whether a fact comes from the context or your training, do not include it.
```

The strictness of this prompt is intentional. Early testing showed the model blending its parametric knowledge with retrieved content — for example, attributing cultural significance to indigenous communities not mentioned in the source documents. The explicit prohibition on outside knowledge and the instruction to flag uncertainty significantly reduced hallucination.

### Context Injection

The top-K retrieved chunks are concatenated and passed as a system message, with the full conversation history and the new user query appended:

```
System: [retrieved context]

User: [turn 1]
Assistant: [turn 1 response]
User: [turn 2]
...
User: [current query]
```

Separating context into the system role and conversation into the user/assistant roles gives the model a clear distinction between grounding material and dialogue history.

### Why K=4

Retrieving 4 chunks provides enough context for multi-faceted questions (e.g. "what are the threats and conservation measures for X?") without exceeding the model's effective context window or introducing irrelevant noise. For simpler factual queries the top chunk is usually sufficient, and the additional chunks provide harmless redundancy.

---

## Retrieval Flow

1. User submits a query via the CLI
2. Query is embedded using `nomic-embed-text` (same model used at ingest time)
3. ChromaDB performs cosine similarity search against all stored chunk embeddings, returning the top 4 matches along with their source file metadata
4. Retrieved chunks are injected into the system prompt alongside full conversation history
5. `llama3:latest` generates a streamed response grounded in the retrieved context
6. The answer streams to the terminal word-by-word, followed by source filenames for full transparency

---

## Known Limitations

### Pronoun Resolution in Follow-up Queries

The retrieval step embeds the raw user query each turn. Vague follow-up questions like "what threatens them?" are embedded without knowing what "them" refers to, so ChromaDB may retrieve chunks from unrelated species. The LLM can sometimes compensate using conversation history, but retrieval quality degrades for pronoun-heavy follow-ups.

The correct fix is **query contextualization** — rewriting the follow-up as a standalone query before embedding (e.g. rewriting "what threatens them?" to "what threatens polar bears?" using conversation history). This was prototyped but removed because the rewriting step introduced its own failure modes, adding latency and occasionally producing over-verbose queries. Self-contained questions are recommended for best results.

### Broad Inventory Queries

Questions like "which species in your knowledge base are critically endangered?" require the model to reason across all 15 documents simultaneously. Since retrieval only returns 4 chunks, broad inventory questions may return incomplete answers. A metadata filtering layer — storing conservation status as a ChromaDB metadata field and filtering directly — would resolve this cleanly in a production system.

### Local Model Capability

`llama3:8b` is capable for factual retrieval tasks but less reliable on complex multi-step reasoning compared to frontier models. For production use, replacing the local LLM with an API-based model (GPT-4, Claude) while keeping the retrieval architecture unchanged would significantly improve answer quality.

---

## File Structure

```
zoo-rag-chatbot/
├── docs/                  # 15 species markdown files (Wikipedia source)
├── chroma_db/             # Persisted ChromaDB vector store (generated)
├── fetch_docs.py          # Fetches and saves Wikipedia articles
├── ingest.py              # Chunks, embeds, and stores docs in ChromaDB
├── chat.py                # CLI chat loop with RAG retrieval and streaming
├── config.py              # Central configuration (models, paths, parameters)
├── requirements.txt       # Python dependencies
├── .env.example           # Template for required environment variables
├── .gitignore             # Excludes .env, chroma_db/, __pycache__/
├── DESIGN.md              # This document
└── transcript.md          # Sample conversation demonstrating the system
```

---

## Design Decisions & Tradeoffs

### Local vs Cloud LLM

Running entirely locally via Ollama means no API costs, no data privacy concerns, and no network dependency after setup. The tradeoff is that `llama3:8b` is less capable than frontier models on complex reasoning. For a domain-specific retrieval task over well-structured documents this is acceptable — the quality of retrieved context matters more than raw model capability.

### No LangChain

LangChain was removed in favour of plain Python for document loading and chunking. This reduces the dependency footprint, makes the chunking logic fully explicit and auditable, and avoids abstracting away behaviour that is core to the system's correctness. The only functionality LangChain provided — directory loading and text splitting — was straightforward to reimplement.

### Multi-turn Conversation

The system maintains conversation history across turns, passing prior exchanges to the LLM alongside fresh retrieved context on each query. This allows the model to answer coherent follow-up questions ("what is being done to protect it?") without the user repeating context. The limitation is that retrieval remains query-based and does not use conversation history to resolve pronouns — see Known Limitations above.

### Streaming Output

Responses stream token-by-token to the terminal rather than appearing all at once. This is purely a UX choice — it eliminates the perception of the system hanging during generation and makes the interaction feel more natural.

---

## Running the Project

```bash
# 1. Create and activate environment
conda create -n zoo-rag python=3.11
conda activate zoo-rag

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull Ollama models
ollama pull llama3:latest
ollama pull nomic-embed-text

# 4. Fetch documents
python fetch_docs.py

# 5. Ingest into ChromaDB
python ingest.py

# 6. Start chatting
python chat.py
```
