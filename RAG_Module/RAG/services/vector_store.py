from ..models import Document,DocumentChunk

def store_document_chunks(document_name,file_type,chunks,embeddings):
    document=Document.objects.create(
        name=document_name,
        file_type=file_type
    )

    for chunk,embedding in zip(chunks,embeddings):
        DocumentChunk.objects.create(
            document=document,
            content=chunk,
            embedding=embedding
        )

    return document