from django.shortcuts import render, redirect
from django.http import JsonResponse,FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms import modelformset_factory
from .chatbot_logic import get_ai_response
from .models import KnowledgeBase, KnowledgeBaseFile
from .forms import CreateKBForm, KnowledgeBaseFileForm
from django.contrib import messages
from .report_generator import generate_report_from_files, generate_report_from_kb,generate_chat_response, create_vector_store1
import os
import logging
from django.shortcuts import get_object_or_404,redirect

logger = logging.getLogger(__name__)

@csrf_exempt
@csrf_exempt
def chat(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input')
        company_name = request.POST.get('company', '')
        kb_id = request.POST.get('kb_id')
        
        # Add proper validation and logging
        if not user_input:
            return JsonResponse({'response': "Please enter a question."})
            
        if not company_name:
            return JsonResponse({'response': "Please select a company before asking questions."})
            
        if not kb_id:
            return JsonResponse({'response': "Please select a knowledge base before asking questions."})
            
        # Look up the knowledge base name from the ID
        try:
            from chatbot.models import KnowledgeBase
            kb_name = kb_id
            
            # Now call generate_chat_response with the actual kb_name
            ai_response = generate_chat_response(user_input, company_name, kb_name)
            return JsonResponse({'response': ai_response})
        except KnowledgeBase.DoesNotExist:
            return JsonResponse({'response': f"Knowledge base with ID {kb_id} not found. Please select a valid knowledge base."})
        except Exception as e:
            logger.error(f"Error in chat view: {e}")
            return JsonResponse({'response': "An error occurred while processing your request. Please try again."})
    else:
        return render(request, 'chatbot.html')

def index(request):
    """
    View function for the home page of the chatbot.
    """
    # Get list of companies for the dropdown
    companies = KnowledgeBase.objects.values_list('company', flat=True).distinct()
    
    # Default if no companies exist
    if not companies:
        companies = ["Central Bank of Bahrain"]
    
    context = {
        'companies': companies,
    }
    return render(request, 'index.html', context)




def create_knowledge_base(request):
    """
    View function to create a new knowledge base
    """
    selected_company = request.GET.get('company', 'Default Company')
    
    if request.method == 'POST':
        kb_form = CreateKBForm(request.POST, company=selected_company)
        
        if kb_form.is_valid():
            try:
                # Create the knowledge base
                kb = kb_form.save()
                
                # Handle multiple file uploads
                files = request.FILES.getlist('files')
                for f in files:
                    KnowledgeBaseFile.objects.create(knowledge_base=kb, file=f)
                kb_name = kb.name
                create_vector_store1(files, kb_name, selected_company)
                
                messages.success(request, f"Knowledge base '{kb.name}' created successfully with {len(files)} files.")
                return redirect('index')
            except Exception as e:
                messages.error(request, f"Error creating knowledge base: {str(e)}")
                
                
    else:
        kb_form = CreateKBForm(company=selected_company)
    
    context = {
        'form': kb_form,
        'selected_company': selected_company
    }
    return render(request, 'create_kb.html', context)

def get_knowledge_bases(request):
    """AJAX view to get knowledge bases for a company"""
    company = request.GET.get('company', '')
    
    print(f"get_knowledge_bases called with company: '{company}'")
    
    if company:
        folder_path = "media/vector_stores/" + company
        file_names = os.listdir(folder_path)

        #knowledge_bases = KnowledgeBase.objects.filter(company=company).values('id', 'name')
        result = {'knowledge_bases': file_names}
        print(f"Returning {len(file_names)} knowledge bases: {result}")
        print("string" , JsonResponse(result))
        return JsonResponse(result)
    else:
        print("No company provided, returning empty list")
        return JsonResponse({'knowledge_bases': []})



def generate_report(request):
    """Handle report generation requests"""
    if request.method == 'POST':
        try:
            # Get parameters from the request
            company_name = request.POST.get('company', '')
            kb_id = request.POST.get('kb_id', None)
            
            if not company_name:
                return JsonResponse({'success': False, 'message': 'Company name is required'})
            
            # Check if we're using an existing KB or creating a new one
            if kb_id:
                # Using existing KB
                kb = get_object_or_404(KnowledgeBase, id=kb_id)
                kb_name = kb.name
                
                # Generate report from KB
                result = generate_report_from_kb(company_name, kb_name)
                
                if result['success']:
                    # Return the path to the generated report for download
                    return JsonResponse({
                        'success': True, 
                        'message': result['message'],
                        'report_url': f"/download-report/{os.path.basename(result['report_path'])}/",
                    })
                else:
                    return JsonResponse({'success': False, 'message': result['message']})
                
            else:
                # Check if files were uploaded
                files = request.FILES.getlist('files')
                if not files:
                    return JsonResponse({'success': False, 'message': 'No files uploaded'})
                
                # Generate KB name
                import datetime
                kb_name = f"{company_name.replace(' ', '')}{datetime.date.today().strftime('%Y%m%d')}"
                
                # Generate report from files
                result = generate_report_from_files(company_name, kb_name, files)
                
                if result['success']:
                    # Return the path to the generated report for download
                    return JsonResponse({
                        'success': True, 
                        'message': result['message'],
                        'report_url': f"/download-report/{os.path.basename(result['report_path'])}/",
                    })
                else:
                    return JsonResponse({'success': False, 'message': result['message']})
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})
    
    # If not a POST request, return error
    return JsonResponse({'success': False, 'message': 'Invalid request method'})



def download_report(request, report_path):
    """Handle report download requests"""
    try:
        # Search for the report in the report directory
        from django.conf import settings
        import os
        
        # Find the full path of the report
        for root, dirs, files in os.walk(settings.MEDIA_ROOT):
            for file in files:
                if file == report_path:
                    file_path = os.path.join(root, file)
                    
                    # Set the appropriate content type based on file extension
                    content_type = 'application/pdf' if file_path.lower().endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    
                    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    return response
        
        # If report not found
        messages.error(request, f"Report not found: {report_path}")
        return redirect('index')
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        messages.error(request, f"Error downloading report: {str(e)}")
        return redirect('index')