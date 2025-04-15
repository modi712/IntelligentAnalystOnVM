from django.urls import path,  include
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from chatbot import views
from .views import login_view, logout_view




urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('create-knowledge-base/', views.create_knowledge_base, name='create_knowledge_base'),
    path('get-knowledge-bases/', views.get_knowledge_bases, name='get_knowledge_bases'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('download-report/<path:report_path>/', views.download_report, name='download_report'),
]

# Add this to serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)