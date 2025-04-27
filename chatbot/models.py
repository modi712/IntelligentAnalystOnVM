from django.db import models
from django.utils import timezone
import os

def kb_file_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/knowledge_bases/<kb_name>/<filename>
    return f'knowledge_bases/{instance.knowledge_base.name}/{filename}'

class KnowledgeBase(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    company = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class KnowledgeBaseFile(models.Model):
    knowledge_base = models.ForeignKey(KnowledgeBase, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to=kb_file_path)
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return os.path.basename(self.file.name)
    
class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Create required directories when a company is saved
        result = super().save(*args, **kwargs)
        
        # Create directories
        from django.conf import settings
        import os
        
        # Create knowledge_bases directory
        kb_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_bases', self.name)
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir)
        
        # Create vector_stores directory
        vs_dir = os.path.join(settings.MEDIA_ROOT, 'vector_stores', self.name)
        if not os.path.exists(vs_dir):
            os.makedirs(vs_dir)
            
        return result
    


class Report(models.Model):
    company = models.CharField(max_length=255)
    kb_name = models.CharField(max_length=255)
    report_path = models.CharField(max_length=1024)
    report_type = models.CharField(max_length=50, default="excel")  # Values: excel, pdf, pptx, qa_excel
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company} - {self.kb_name} ({self.report_type}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"