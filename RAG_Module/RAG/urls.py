from django.urls import path
from .views import DocumentUploadView,RetrievalView

urlpatterns = [
    path("document/upload/",DocumentUploadView.as_view()),
    path("retrieve/",RetrievalView.as_view())
]
