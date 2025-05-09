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
    path('add-company/', views.add_company, name='add_company'),
    path('chat/', views.chat, name='chat'),
    path('create-knowledge-base/', views.create_knowledge_base, name='create_knowledge_base'),
    path('get-knowledge-bases/', views.get_knowledge_bases, name='get_knowledge_bases'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('get-reports/', views.get_reports, name='get_reports'),
    path('get-report-content/<path:report_path>/', views.get_report_content, name='get_report_content'),
    path('download-report/<path:report_path>/', views.download_report, name='download_report'),
    path('generate-qa-report/', views.generate_qa_report, name='generate_qa_report'),
    path('upload-ground-truths/', views.upload_ground_truths, name='upload_ground_truths'),
    path('get-session-reports/', views.get_session_reports, name='get_session_reports'),
]

# Add this to serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)