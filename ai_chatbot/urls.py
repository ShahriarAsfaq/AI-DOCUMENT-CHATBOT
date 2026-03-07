from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('ai_chatbot.chat.urls')),
    path('api/documents/', include('ai_chatbot.documents.urls')),
    path('api/rag/', include('ai_chatbot.rag.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
