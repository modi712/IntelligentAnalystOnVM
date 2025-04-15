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