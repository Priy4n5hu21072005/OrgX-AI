from rest_framework import serializers

class DocumentUploadSerializer(serializers.Serializer):
    file=serializers.FileField()

class RetrievalSerializer(serializers.Serializer):
    query=serializers.CharField()
    top_k=serializers.IntegerField(default=5,min_value=1,max_value=20)
    