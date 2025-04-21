from django.shortcuts import render, redirect
from django.http import JsonResponse,FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms import modelformset_factory
from .chatbot_logic import get_ai_response
from .models import KnowledgeBase, KnowledgeBaseFile
from .forms import CreateKBForm, KnowledgeBaseFileForm
from django.contrib import messages
from .report_generator1 import  generate_chat_response, create_vector_store1,generate_excel_report_from_kb
import os
import logging
from django.shortcuts import get_object_or_404,redirect
import json
from openpyxl import load_workbook


logger = logging.getLogger(__name__)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Load users from JSON file
        json_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')
        
        try:
            with open(json_file_path, 'r') as f:
                users_data = json.load(f)
            
            # Check credentials
            authenticated = False
            user_info = None
            
            for user in users_data.get('users', []):
                if user['username'] == username and user['password'] == password:
                    authenticated = True
                    user_info = user
                    break
            
            if authenticated:
                # Store user info in session
                request.session['user'] = {
                    'username': user_info['username'],
                    'full_name': user_info['full_name'],
                    'role': user_info['role'],
                    'is_authenticated': True
                }
                messages.success(request, f"Welcome back, {user_info['full_name']}!")
                return redirect('index')
            else:
                messages.error(request, "Invalid username or password")
                
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return render(request, 'login.html')

def logout_view(request):
    # Clear the session
    if 'user' in request.session:
        del request.session['user']
    messages.success(request, "You have been logged out successfully")
    return redirect('login')


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
    # Get list of companies from the database
    from .models import Company
    companies = list(Company.objects.values_list('name', flat=True))
    
    # Default if no companies exist
    if not companies:
        # Add default company if none exist
        default_company = "Central Bank of Bahrain"
        Company.objects.create(name=default_company)
        companies = [default_company]

    context = {
        'companies': companies,
    }
    return render(request, 'index.html', context)

def add_company(request):
    """Add a new company to the system"""
    if request.method == 'POST':
        try:
            # Get company name from form
            company_name = request.POST.get('company_name', '').strip()
            
            if not company_name:
                return JsonResponse({'success': False, 'message': 'Company name is required'})
            
            # Check if company already exists
            from .models import Company
            if Company.objects.filter(name=company_name).exists():
                return JsonResponse({'success': False, 'message': 'Company already exists'})
            
            # Create new company (directories are created in the save method)
            company = Company.objects.create(name=company_name)
            
            return JsonResponse({
                'success': True, 
                'message': f'Company "{company_name}" added successfully',
                'company_name': company_name
            })
            
        except Exception as e:
            logger.error(f"Error adding company: {e}")
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def create_knowledge_base(request):
    """
    View function to create a new knowledge base
    """
    selected_company = request.GET.get('company', 'Default Company')

     # Ensure company exists
    from .models import Company
    if not Company.objects.filter(name=selected_company).exists():
        Company.objects.create(name=selected_company)
    
    if request.method == 'POST':
        kb_form = CreateKBForm(request.POST, company=selected_company)
        
        if kb_form.is_valid():
            try:
                # Create the knowledge base
                kb = kb_form.save()


                 # Add the company to the context for the response
                new_company = selected_company
                
                # Handle multiple file uploads
                files = request.FILES.getlist('files')
                for f in files:
                    KnowledgeBaseFile.objects.create(knowledge_base=kb, file=f)
                
                kb_name = kb.name
                
                # Sanitize the kb_name for use as collection name
                import re
                sanitized_kb_name = re.sub(r'[^a-zA-Z0-9_-]', '_', kb_name)
                # Ensure it starts and ends with alphanumeric character
                if not sanitized_kb_name[0].isalnum():
                    sanitized_kb_name = 'kb_' + sanitized_kb_name
                if len(sanitized_kb_name) > 0 and not sanitized_kb_name[-1].isalnum():
                    sanitized_kb_name = sanitized_kb_name + '1'
                # Ensure minimum length of 3
                if len(sanitized_kb_name) < 3:
                    sanitized_kb_name = sanitized_kb_name + '_db'
                # Ensure maximum length of 63
                sanitized_kb_name = sanitized_kb_name[:63]
                
                # Create vector store
                try:
                    from .report_generator1 import create_vector_store1
                    retriever = create_vector_store1(files, sanitized_kb_name, selected_company)
                    if retriever is None:
                        messages.error(request, "Failed to create vector store. Check logs for details.")
                    else:
                        messages.success(request, f"Knowledge base '{kb.name}' created successfully with {len(files)} files for company '{new_company}'.")
                except Exception as e:
                    logger.error(f"Error creating vector store: {e}")
                    messages.error(request, f"Error creating knowledge base: {str(e)}")


                
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
        
        # Check if directory exists
        if not os.path.exists(folder_path):
            # Create directory if it doesn't exist
            os.makedirs(folder_path)
            return JsonResponse({'knowledge_bases': []})
            
        file_names = os.listdir(folder_path)
        result = {'knowledge_bases': file_names}
        print(f"Returning {len(file_names)} knowledge bases: {result}")
        return JsonResponse(result)
    else:
        print("No company provided, returning empty list")
        return JsonResponse({'knowledge_bases': []})



def generate_report(request):
    """
    View function to generate a report for a knowledge base
    """
    if request.method == 'POST':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            company_name = data.get('company')
            kb_name = data.get('kb_name')
            report_type = data.get('report_type', 'excel')  
            
            # Validate input
            if not company_name or not kb_name:
                return JsonResponse({
                    'success': False,
                    'message': 'Company name and knowledge base name are required'
                })
            
            # Generate the requested report type
            if report_type == 'excel':
                result = generate_excel_report_from_kb(company_name, kb_name)

             # If successful, save the report information
            if result['success']:
                from .models import Report
                Report.objects.create(
                    company=company_name,
                    kb_name=kb_name,
                    report_path=result['report_path'],
                    report_type=report_type
                )
            
            # Return the result
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return JsonResponse({
                'success': False,
                'message': f"Error: {str(e)}"
            })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)
    

# Add this new function

def get_reports(request):
    """
    View function to get all generated reports
    """
    try:
        from .models import Report
        reports = Report.objects.all()
        
        reports_data = []
        for report in reports:
            reports_data.append({
                'id': report.id,
                'company': report.company,
                'kb_name': report.kb_name,
                'report_type': report.report_type,
                'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
                'report_path': report.report_path
            })
        
        return JsonResponse({'success': True, 'reports': reports_data})
    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        })
    
def get_report_content(request, report_path):
    """
    View function to read Excel report content and return it as JSON
    """
    try:
        # Check if file exists
        if not os.path.exists(report_path):
            return JsonResponse({
                'success': False,
                'message': 'Report file not found'
            }, status=404)
        
        # Check if file is an Excel file
        if not report_path.endswith('.xlsx'):
            return JsonResponse({
                'success': False,
                'message': 'File is not an Excel report'
            }, status=400)
        
        # Load the workbook
        wb = load_workbook(filename=report_path)
        ws = wb.active
        
        # Extract the company name from the title cell (A1)
        title = ws['A1'].value
        company_name = title.split(' - ')[0] if ' - ' in title else 'Company'
        
        # Initialize data structure
        report_data = {
            'title': title,
            'company': company_name,
            'categories': []
        }
        
        # Process the rows and collect the data
        current_category = None
        category_questions = []
        
        # Start from row 4 (after headers)
        for row in range(4, ws.max_row + 1):
            # Check if this is a category row (merged cells)
            merged_cell_ranges = [str(cell_range) for cell_range in ws.merged_cells.ranges]
            current_cell = f'A{row}:C{row}'
            
            if current_cell in merged_cell_ranges:
                # If we already have a category, add it to the report data
                if current_category and category_questions:
                    report_data['categories'].append({
                        'name': current_category,
                        'questions': category_questions
                    })
                
                # Start a new category
                current_category = ws[f'A{row}'].value
                category_questions = []
            else:
                # Regular question row
                question = ws[f'B{row}'].value
                answer = ws[f'C{row}'].value
                
                if question and answer:
                    category_questions.append({
                        'question': question,
                        'answer': answer
                    })
        
        # Add the last category if there is one
        if current_category and category_questions:
            report_data['categories'].append({
                'name': current_category,
                'questions': category_questions
            })
        
        return JsonResponse({
            'success': True,
            'report_data': report_data
        })
        
    except Exception as e:
        logger.error(f"Error reading report content: {e}")
        return JsonResponse({
            'success': False,
            'message': f"Error reading report content: {str(e)}"
        }, status=500)


    

def download_report(request, report_path):
    """
    View function to download a generated report
    """
    try:
        # Validate the file exists
        if not os.path.exists(report_path):
            return JsonResponse({
                'success': False,
                'message': 'Report file not found'
            }, status=404)
        
        # Get the file extension
        file_extension = os.path.splitext(report_path)[1].lower()
        
        # Set the content type based on file extension
        content_types = {
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        content_type = content_types.get(file_extension, 'application/octet-stream')

         # Get view parameter - if true, try to display in browser
        view = request.GET.get('view', 'false').lower() == 'true'
        
        # Create a FileResponse
        response = FileResponse(open(report_path, 'rb'), content_type=content_type)

         # Set the content disposition based on the view parameter
        if view and file_extension == '.pdf':
            # PDF files can be displayed in-browser
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(report_path)}"'
        else:
            # All other files should be downloaded
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_path)}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return JsonResponse({
            'success': False,
            'message': f"Error: {str(e)}"
        }, status=500)


    # Export the login and logout views explicitly
__all__ = [
    'login_view', 
    'logout_view', 
    'index', 
    'chat', 
    'create_knowledge_base', 
    'get_knowledge_bases', 
    'generate_report', 
    'download_report',
    'generate_chat_response',
    'generate_report_from_files',
    'generate_report_from_kb',
    'generate_excel_report_from_kb',
    'generate_excel_report'
]