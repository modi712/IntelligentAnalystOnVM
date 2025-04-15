from django import forms
from .models import KnowledgeBase, KnowledgeBaseFile
import datetime

class CreateKBForm(forms.ModelForm):
    """
    Form for creating a new knowledge base
    """
    class Meta:
        model = KnowledgeBase
        fields = ['name', 'company', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super(CreateKBForm, self).__init__(*args, **kwargs)
        
        if company:
            # Generate default name based on company and date
            default_name = f"{company.replace(' ', '')}{datetime.date.today().strftime('%Y%m%d')}"
            self.fields['name'].initial = default_name
            self.fields['company'].initial = company
            self.fields['company'].widget = forms.HiddenInput()

class KnowledgeBaseFileForm(forms.ModelForm):
    """
    Form for uploading files to a knowledge base
    """
    class Meta:
        model = KnowledgeBaseFile
        fields = ['file']