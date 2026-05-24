import os
import chromadb
import ollama
from config import DOCS_DIR, CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, EMBED_MODEL

def load_docs():
    print("Loading documents...")
    docs = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(DOCS_DIR, filename)
            with open(filepath, "r") as f:
                text = f.read()
            docs.append({"text": text, "source": filepath})
    print(f"  Loaded {len(docs)} documents")
    return docs

def chunk_docs(docs):
    print("Chunking documents...")
    chunks = []
    for doc in docs:
        text = doc["text"]
        source = doc["source"]

        # First split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Further split any paragraph that exceeds CHUNK_SIZE
        split_paras = []
        for para in paragraphs:
            if len(para) <= CHUNK_SIZE:
                split_paras.append(para)
            else:
                # Hard split with overlap
                start = 0
                while start < len(para):
                    split_paras.append(para[start:start + CHUNK_SIZE])
                    start += CHUNK_SIZE - CHUNK_OVERLAP

        # Merge small paragraphs into chunks up to CHUNK_SIZE
        current_chunk = ""
        for para in split_paras:
            if len(current_chunk) + len(para) > CHUNK_SIZE and current_chunk:
                chunks.append({"text": current_chunk.strip(), "source": source})
                current_chunk = current_chunk[-CHUNK_OVERLAP:] + " " + para
            else:
                current_chunk += " " + para

        if current_chunk.strip():
            chunks.append({"text": current_chunk.strip(), "source": source})

    print(f"  Created {len(chunks)} chunks")
    return chunks

def embed_and_store(chunks):
    print("Embedding and storing chunks...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection("zoo_docs")
    except:
        pass
    collection = client.create_collection("zoo_docs")

    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [f"chunk_{i + j}" for j in range(len(batch))]
        metadatas = [{"source": c["source"]} for c in batch]

        embeddings = []
        for text in texts:
            response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
            embeddings.append(response.embedding)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        print(f"  Stored chunks {i} to {i + len(batch)}")

    print(f"\nDone! {len(chunks)} chunks stored in ChromaDB")

def main():
    docs = load_docs()
    chunks = chunk_docs(docs)
    embed_and_store(chunks)

if __name__ == "__main__":
    main()
