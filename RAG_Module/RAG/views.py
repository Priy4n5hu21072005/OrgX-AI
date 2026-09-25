from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pathlib import Path

from .serializers import DocumentUploadSerializer
from .services.document_parser import extract_text
from .services.chunking import chunk_text
from .services.embedding import embedding_model
from .services.vector_store import store_document_chunks
# Create your views here.

class DocumentUploadView(APIView):
    def post(self,request):
        serializer=DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        file=serializer.validated_data["file"]

        try:
            text=extract_text(file)  
            chunks=chunk_text(text)
            embeddings=[
                embedding_model.get_text_embedding(chunk)
                for chunk in chunks 
            ]

            document=store_document_chunks(
                document_name=file.name,
                file_type=Path(file.name).suffix.lower(),
                chunks=chunks,
                embeddings=embeddings
            )
            return Response(
                            {
                                "message":"Document uploaded Successfully",
                                "document_id":document.id,
                                "filename":file.name,
                                "chunks":len(chunks)
                            }
                        )
            
        except ValueError as e:
            return Response(
                {
                    "error":str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )