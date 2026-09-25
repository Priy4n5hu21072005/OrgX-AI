from django.db import models 
from pgvector.django import VectorField

class Document(models.Model):
    name=models.CharField(max_length=255)
    file_type=models.CharField(max_length=20)
    uploaded_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class DocumentChunk(models.Model):
    document=models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    content=models.TextField()
    embedding=VectorField(dimensions=384)

    def __str__(self):
        return f"{self.document.name} - Chunk {self.id}"
    
