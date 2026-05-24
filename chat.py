import os
import chromadb
import ollama
from config import CHROMA_DIR, EMBED_MODEL, OLLAMA_MODEL, TOP_K

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection("zoo_docs")

def retrieve(query, collection):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    query_embedding = response.embedding
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K
    )
    
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    return chunks, sources

def contextualize_query(query, conversation_history):
    # Only bother if there's prior context
    if not conversation_history:
        return query
    
    # Ask the LLM to rewrite the query as a standalone question
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        for m in conversation_history[-4:]  # last 2 exchanges
    )
    
    rewrite_prompt = f"""Given this conversation history:
{history_text}

Rewrite the following question as a fully self-contained search query with no pronouns or references to prior context. Return only the rewritten query, nothing else.

Question: {query}
Rewritten:"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": rewrite_prompt}]
    )
    rewritten = response["message"]["content"].strip()
    return rewritten

def build_system_prompt(chunks):
    context = "\n\n---\n\n".join(chunks)
    return f"""You are a zoo and wildlife conservation assistant with access to a specific document library.
Answer questions ONLY using the context provided below.
Do NOT use any outside knowledge or training data.
If the answer cannot be found in the context, say exactly: "I don't have that information in my knowledge base."
Never make up species, statistics, or facts not present in the context.
"If you are unsure whether a fact comes from the context or your training, do not include it."

Context:
{context}"""

def chat():
    print("🦁 Zoo & Conservation Knowledge Assistant")
    print("Type 'quit' to exit\n")
    
    collection = get_collection()
    conversation_history = []
    
    while True:
        query = input("You: ").strip()
        
        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        
        # Retrieve fresh context for each query
        search_query = contextualize_query(query, conversation_history)
        # print(f"  [debug] search query: {search_query}")
        chunks, sources = retrieve(search_query, collection)
        system_prompt = build_system_prompt(chunks)
        
        # Build messages: system context + full conversation history + new query
        messages = (
            [{"role": "system", "content": system_prompt}]
            + conversation_history
            + [{"role": "user", "content": query}]
        )
        
        print("\nAssistant: ", end="", flush=True)
        
        stream = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=True
        )
        
        # Collect full response for history
        full_response = ""
        for chunk in stream:
            content = chunk["message"]["content"]
            print(content, end="", flush=True)
            full_response += content
        
        # Append this exchange to history
        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": full_response})
        
        unique_sources = list(set(
            os.path.basename(s) for s in sources
        ))
        print(f"\n\n📚 Sources: {', '.join(unique_sources)}\n")



if __name__ == "__main__":
    chat()