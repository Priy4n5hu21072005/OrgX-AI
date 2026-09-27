from ..models import DocumentChunk
from .embedding import embedding_model

from pgvector.django import CosineDistance

def retrieval_chunks(query,top_k=5):
    query_embedding=embedding_model.get_text_embedding(query)
    chunks = (DocumentChunk.objects.annotate(
        distance=CosineDistance(
            "embedding",query_embedding
        )
    ).order_by("distance")[:top_k]
    )

    result=[]

    for chunk in chunks :
       
        result.append({
            "content":chunk.content,
            "score":1-chunk.distance
        })
    return result