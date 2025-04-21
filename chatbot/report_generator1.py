import os
import uuid
import datetime
import logging
from pathlib import Path
from django.conf import settings
from uuid import uuid4
import shutil
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import LLMChain
import json
from openpyxl import Workbook 
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side 


# Configure logger
logger = logging.getLogger(__name__)

# Initialize constants
MEDIA_ROOT = settings.MEDIA_ROOT
REPORTS_DIR = os.path.join(MEDIA_ROOT, "reports")
VECTOR_STORES_DIR = os.path.join(MEDIA_ROOT, "vector_stores")

# Initialize embeddings and text splitter
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)


# Create directory structure functions
def ensure_dir_exists(path):
    """Ensure the directory exists, create if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# Initialize LLM for report generation
try:
    from .api_key import GROQ_API_KEY  # Import API key
    from langchain_groq import ChatGroq as Groq
    llm = Groq(api_key='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', model_name="llama-3.3-70b-versatile")
except (ImportError, Exception) as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None

def get_company_dir(company_name):
    """Get company directory path and create if doesn't exist."""
    company_path = os.path.join(VECTOR_STORES_DIR, company_name)
    return ensure_dir_exists(company_path)

def get_kb_dir(company_name, kb_name):
    """Get knowledge base directory path and create if doesn't exist."""
    kb_path = os.path.join(get_company_dir(company_name), kb_name)
    return ensure_dir_exists(kb_path)




def generate_excel_report(company_name, kb_name, retriever):
    """Generate an Excel report with answers to predefined questions"""
    logger.info(f"Generating Excel report for {company_name}/{kb_name}")
    
    # Create a new workbook and select the active worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Investment Analysis"
    
    # Define styles
    header_font = Font(bold=True, size=12)
    category_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="CFCFCF", end_color="CFCFCF", fill_type="solid")
    category_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add report title
    ws.merge_cells('A1:C1')
    ws['A1'] = f"{company_name} - Investment Analysis Report"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')
    
    # Add headers
    ws['A3'] = "Category"
    ws['B3'] = "Question"
    ws['C3'] = "Answer"
    
    for cell in ['A3', 'B3', 'C3']:
        ws[cell].font = header_font
        ws[cell].fill = header_fill
        ws[cell].border = thin_border
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 60
    
    # Define questions by category
    questions = {
        "Business Model": [
            "Size of opportunity (by revenue)",
            "Size of opportunity (by profits)",
            "Asset light/heavy (Capex/Sales)"
        ],
        "Product and Technology": [
            "Prototype ready",
            "Quality of prototype",
            "IP in the technology high / or other IPs",
            "Is there very high R&D in this activity"
        ],
        "Customer/Value Proposition": [
            "Value they bring to the customer",
            "Has the business got a strong moat?",
            "Is the business differentiated relative to peers?"
        ],
        "Life Cycle/Competitive Analysis": [
            "Is it early stage of life cycle",
            "Is there high competitive intensity now?",
            "Is there high competitive intensity likely in 5 years time"
        ],
        "Market View": [
            "Are street analysts very positive?",
            "Is it backed by top investor/group? (strategic side)"
        ],
        "Financials": [
            "Is the company demonstrating very fast revenue growth? (>=30% 3yr-CAGR)",
            "Is the path to profitability very clear?",
            "Does the unit economics make sense?"
        ],
        "Management Quality": [
            "Does management have high quality in expertise?",
            "Does management appear honest/trustworthy/Ethical?"
        ],
        "Regulatory Risk": [
            "Governmental intervention: positive or negative?"
        ],
        "Promotor Quality": [
            "SRT framework (Anuj)"
        ]
    }
    
    # Starting row for data
    row = 4
    
    # Iterate through categories and questions
    for category, category_questions in questions.items():
        # Add category row
        ws.merge_cells(f'A{row}:C{row}')
        ws[f'A{row}'] = category
        ws[f'A{row}'].font = category_font
        ws[f'A{row}'].fill = category_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='left')
        for col in ['A', 'B', 'C']:
            ws[f'{col}{row}'].border = thin_border
        row += 1
        
        # Process each question in the category
        for question in category_questions:
            # Format the query for better results
            query = f"For {company_name}, {question}. Please provide a concise answer based on the available information."
            
            # Get answer from the retriever and LLM
            answer = run_query(query, retriever)
            
            # Add to worksheet
            ws[f'A{row}'] = ""  # No category in question rows
            ws[f'B{row}'] = question
            ws[f'C{row}'] = answer
            ws[f'C{row}'].alignment = Alignment(wrap_text=True, vertical='top')

            # Add these styles to make the text more readable
            ws[f'C{row}'].font = Font(name='Calibri', size=10)

            # Adjust row height for better readability
            ws.row_dimensions[row].height = max(18, min(40, 15 * (answer.count('\n') + 1)))
            
            # Apply borders
            for col in ['A', 'B', 'C']:
                ws[f'{col}{row}'].border = thin_border
                ws[f'{col}{row}'].alignment = Alignment(wrap_text=True, vertical='top')
            
            row += 1
    
    # Save the workbook
    excel_dir = os.path.join(get_kb_dir(company_name, kb_name), "excel")
    ensure_dir_exists(excel_dir)
    excel_path = os.path.join(excel_dir, f"{company_name}_{kb_name}_analysis.xlsx")
    wb.save(excel_path)
    
    logger.info(f"Excel report saved to {excel_path}")
    return excel_path


def generate_excel_report_from_kb(company_name, kb_name):
    """Generate an Excel report from an existing knowledge base 
    Args:
        company_name: Name of the company to analyze
        kb_name: Name of the knowledge base to use
    """

    try:
        logger.info(f"Generating Excel report for {company_name}/{kb_name}")
        
        # Check if KB name is None or empty
        if not kb_name:
            return {
                'success': False,
                'message': "Please select a knowledge base first."
            }
            
        # Check if company name is None or empty
        if not company_name:
            return {
                'success': False,
                'message': "Please select a company first."
            }
    
        # Get the vector store directory path
        kb_dir = get_kb_dir(company_name, kb_name)
        persist_dir = os.path.join(kb_dir, "vector_store")
        
        if not os.path.exists(persist_dir):
            logger.warning(f"Vector store for {kb_name} does not exist.")
            return {
                'success': False,
                'message': f"Knowledge base {kb_name} not found for {company_name}."
            }
        
        # Load the vector store
        vectorstore = Chroma(
            collection_name=kb_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        
        # Create retriever
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        
        # Generate the Excel report
        excel_path = generate_excel_report(company_name, kb_name, retriever)
        
        return {
            'success': True,
            'report_path': excel_path,
            'message': f"Generated Excel report for {company_name} from knowledge base {kb_name}"
        }
        
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}")
        return {
            'success': False,
            'message': f"Error generating Excel report: {str(e)}"
        }
    
def runquery(query_text, slide_index, shape_index, page_num, paragraph_index, retriever, ppt=None):
    """Run a query and update a specific shape in the presentation"""
    try:
        # Get the response from the query
        response = run_query(query_text, retriever)
        
        # If no presentation is provided, just return the response
        if ppt is None:
            return response
        
        # Get the slide
        if slide_index < len(ppt.slides):
            slide = ppt.slides[slide_index]
            
            # Update the shape
            if shape_index < len(slide.shapes):
                shape = slide.shapes[shape_index]
                
                if hasattr(shape, 'text_frame'):
                    # If paragraph_index is specified, update only that paragraph
                    if paragraph_index < len(shape.text_frame.paragraphs):
                        shape.text_frame.paragraphs[paragraph_index].text = response
                    else:
                        shape.text_frame.text = response
                
                    text = re.sub(r'\*\*(.*?)\*(?!\*)', r'**\1**', text)
                    return True
        return False
    except Exception as e:
        logger.error(f"Error in runquery: {e}")
        return False
    

def create_vector_store1(files, kb_name, company_name):
    """Create a vector store from uploaded files."""
    logger.info(f"Creating vector store for {company_name}/{kb_name}")
    
    try:
        # Get directories
        kb_dir = get_kb_dir(company_name, kb_name)
        persist_dir = os.path.join(kb_dir, "vector_store")
        ensure_dir_exists(persist_dir)
        
        # Process uploaded files to get text
        all_texts = []
        file_paths = []
        
        # First save the files to disk
        for file_obj in files:
            # Save file to disk
            file_path = os.path.join(kb_dir, file_obj.name)
            with open(file_path, "wb") as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
            file_paths.append(file_path)
            logger.debug(f"Saved file: {file_path}")
        
        # Then process the files to extract text
        for file_path in file_paths:
            if file_path.lower().endswith('.pdf'):
                try:
                    loader = PyPDFLoader(file_path)
                    pages = loader.load_and_split()
                    all_texts.extend([page.page_content for page in pages])
                    logger.debug(f"Processed PDF: {file_path}")
                except Exception as e:
                    logger.error(f"Error processing PDF {file_path}: {e}")
        
        # Create chunks and vectorize
        chunks = text_splitter.create_documents(all_texts)
        uuids = [str(uuid4()) for _ in range(len(chunks))]
        
        # Define max batch size (lower than the 166 limit mentioned in the error)
        MAX_BATCH_SIZE = 100
        
        # Create batches of documents
        total_chunks = len(chunks)
        batches = []
        uuid_batches = []
        
        for i in range(0, total_chunks, MAX_BATCH_SIZE):
            end_idx = min(i + MAX_BATCH_SIZE, total_chunks)
            batches.append(chunks[i:end_idx])
            uuid_batches.append(uuids[i:end_idx])
        
        logger.info(f"Split {total_chunks} documents into {len(batches)} batches of maximum size {MAX_BATCH_SIZE}")
        
        # Create vector store
        vectorstore = Chroma(
            collection_name=kb_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        
        # Add documents in batches
        for i, (batch, uuid_batch) in enumerate(zip(batches, uuid_batches)):
            logger.info(f"Adding batch {i+1}/{len(batches)} with {len(batch)} documents")
            vectorstore.add_documents(documents=batch, ids=uuid_batch)
            
        logger.info(f"Successfully added all {total_chunks} document chunks to vector store")
        
        # Create and return a retriever
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        return retriever
        
    except Exception as e:
        logger.error(f"Error creating vector store: {e}")
        return None

def generate_chat_response(query, company_name, kb_name):
    """Generate a conversational response based on knowledge base content"""
    try:
        logger.info(f"Generating chat response for query: '{query}' using {company_name}/{kb_name}")

         # Check if KB name is None or empty
        if not kb_name:
            return "Please select a knowledge base before asking questions."
        
         # Convert kb_id to kb_name if an ID was passed
        if kb_name and kb_name.isdigit():
            try:
                from chatbot.models import KnowledgeBase
                kb_obj = KnowledgeBase.objects.get(id=int(kb_name))
                kb_name = kb_obj.name
                logger.info(f"Converted kb_id {kb_name} to name: {kb_obj.name}")
            except Exception as e:
                logger.error(f"Error converting kb_id to name: {e}")
                return "There was an error with the knowledge base selection. Please try again."
        
        # Check if KB name is None or empty
        if not kb_name:
            return "Please select a knowledge base before asking questions."
            
        # Check if company name is None or empty
        if not company_name:
            return "Please select a company before asking questions."
        
        # Check if knowledge base exists
        kb_dir = get_kb_dir(company_name, kb_name)
        persist_dir = os.path.join(kb_dir, "vector_store")
        
        if not os.path.exists(persist_dir):
            logger.warning(f"Vector store for {kb_name} does not exist")
            return "I don't have any information about this topic. Please upload relevant documents first."
        
        # Ensure LLM is initialized
        if not llm:
            logger.error("LLM not initialized for chat")
            return "I'm unable to process your request right now. Please try again later."
        
        # Load vector store and create retriever
        try:
            vectorstore = Chroma(
                collection_name=kb_name,
                embedding_function=embeddings,
                persist_directory=persist_dir,
            )
            
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return "I'm having trouble accessing the knowledge base. Please try again later."
        
        # Get relevant documents with proper error handling
        try:
            retrieved_docs = retriever.invoke(query)
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return "I encountered an error while searching for information. Please try again later."
        
        if not retrieved_docs:
            logger.warning(f"No relevant documents found for query: '{query}'")
            return "I couldn't find specific information to answer your question. Could you rephrase or ask about a different topic?"
        
        # Combine document content for context with safety check
        valid_contents = []
        for doc in retrieved_docs:
            if hasattr(doc, 'page_content') and doc.page_content is not None:
                valid_contents.append(doc.page_content)
        
        if not valid_contents:
            logger.warning("Retrieved documents had no valid content")
            return "I found some information but couldn't process it correctly. Please try a different question."
            
        context = "\n\n".join(valid_contents)
        
        # Create prompt template
        prompt = PromptTemplate(
            template="""You are a professional business analyst assistant.
            
            Based on the following context information, provide a well-structured, professional response to the query.
            Make your response comprehensive yet concise.
            Format your response with bullet points where appropriate.
            If you don't know the answer based on the context, say so clearly rather than making up information.
            
            Context: {context}
            
            Query: {query}
            
            Response:""",
            input_variables=["context", "query"]
        )
        
        # Create and run chain with timeout handling
        try:
            chain = LLMChain(llm=llm, prompt=prompt)
            response = chain.invoke({"context": context, "query": query})
            
            if not response or 'text' not in response:
                logger.error("Received empty or invalid response from LLM")
                return "I'm sorry, but I couldn't generate a proper response. Please try again later."
                
            return response['text'].strip()
        except Exception as chain_error:
            logger.error(f"Error in LLM chain: {chain_error}")
            return "I encountered an error while processing your request. Please try again later."
        
    except Exception as e:
        import traceback
        logger.error(f"Error generating chat response: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return "I encountered an error while processing your request. Please try again later."

def run_query(query, retriever):
    """Run a query against the retriever and process with LLM"""
    if not llm:
        return "LLM not initialized. Cannot generate report content."
    
    # Get relevant documents
    retrieved_docs = retriever.invoke(query)
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    
    # Create prompt template
    prompt = PromptTemplate(
        template="""You are a professional business analyst creating a report.
        
        Based on the following context information, provide a well-structured, professional response to the query.
        Make your response comprehensive yet concise, suitable for a business presentation slide.
        
        Important formatting requirements:
        1. Start with a brief summary (1-2 sentences)
        2. Use bullet points for key information (• format)
        3. If providing data or statistics, present them clearly
        4. For any multi-part answers, use numbered lists
        5. Bold important terms or figures using markdown (**term**)
        6. Use short paragraphs with clear spacing between points
        7. Avoid long, dense paragraphs of text
        
        Context: {context}
        
        Query: {query}
        
        Response:""",
        input_variables=["context", "query"]
    )
    
    # Create and run chain
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.invoke({"context": context, "query": query})

    # Process response for better formatting in Excel
    text = response['text'].strip()

    # Convert markdown bullets to proper bullet points for Excel
    text = text.replace('\n• ', '\n• ')
    text = text.replace('\n* ', '\n• ')
    text = text.replace('\n- ', '\n• ')

    # Ensure proper line breaks between bullet points
    text = text.replace('\n\n• ', '\n• ')
    
    return text



    
def get_excel_dir(company_name, kb_name):
    """Get Excel directory path and create if doesn't exist."""
    excel_path = os.path.join(get_kb_dir(company_name, kb_name), "excel")
    return ensure_dir_exists(excel_path)