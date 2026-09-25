from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embedding_model=HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

