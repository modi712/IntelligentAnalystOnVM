import os
import logging
from django.conf import settings # Use Django settings
# Remove direct api_key import if you had one

# Import necessary LangChain classes
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser # For consistent output

from . import api_key # Import API keys if needed

logger = logging.getLogger(__name__) # Use Django logging

# --- Configuration (Now read from settings) ---
LLM_PROVIDER = "groq" # 'groq' or 'gemini'

# Groq Config
GROQ_API_KEY = api_key.GROQ_API_KEY
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

# Gemini Config
GOOGLE_API_KEY = api_key.gemini_api_key
GEMINI_MODEL_NAME = 'gemini-2.5-pro-exp-03-25' 

COMPANY_INFO_FILE = getattr(settings, 'COMPANY_INFO_FILE', os.path.join(settings.BASE_DIR, "home","api.txt"))
COMPANY_NAME =  "Swastik Technologies" # Get from settings or use default
# --- Global Variables ---
llm = None # Will hold the initialized LLM instance
chain = None
company_text = None


def load_system_prompt():
    """Load system prompt from knowledge_base.txt file."""
    kb_path = os.path.join(settings.BASE_DIR, "knowledge_base.txt")
    try:
        logger.debug(f"Attempting to load system prompt from: {kb_path}")
        if not os.path.exists(kb_path):
            logger.warning(f"Knowledge base file does not exist: {kb_path}")
            return None
        with open(kb_path, "r", encoding="utf-8") as file:
            content = file.read()
            logger.info(f"Successfully loaded system prompt from {kb_path}.")
            return content
    except FileNotFoundError:
        logger.error(f"Error: Knowledge base file '{kb_path}' not found.")
        return None
    except IOError as e:
        logger.error(f"Error reading knowledge base file {kb_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred loading knowledge base file {kb_path}: {e}", exc_info=True)
        return None




def initialize_chatbot():
    global llm, chain, company_text
    is_initialized = (llm is not None and chain is not None and company_text is not None and not company_text.startswith("Error:"))

    if is_initialized:
        return # Already initialized

    # --- Initialize LLM Instance based on Provider ---
    if llm is None: # Only initialize LLM if not already done
        logger.info(f"Attempting to initialize LLM provider: {LLM_PROVIDER}")
        if LLM_PROVIDER == "groq":
            if not GROQ_API_KEY:
                logger.error("Cannot initialize Groq: GROQ_API_KEY is missing in settings/environment.")
                llm = None
            else:
                try:
                    logger.info(f"Initializing ChatGroq model: {GROQ_MODEL_NAME}")
                    llm = ChatGroq(
                        groq_api_key=GROQ_API_KEY,
                        model_name=GROQ_MODEL_NAME,
                        temperature=0.2
                    )
                    logger.info("ChatGroq Initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize ChatGroq. Check API Key and Model Name ({GROQ_MODEL_NAME}). Error: {e}", exc_info=True)
                    llm = None

        elif LLM_PROVIDER == "gemini":
            if not GOOGLE_API_KEY:
                logger.error("Cannot initialize Gemini: GOOGLE_API_KEY is missing in settings/environment.")
                llm = None
            else:
                try:
                    logger.info(f"Initializing ChatGoogleGenerativeAI model: {GEMINI_MODEL_NAME}")
                    # Note: Model names might be like "gemini-1.5-flash", "gemini-pro", etc.
                    llm = ChatGoogleGenerativeAI(
                        model=GEMINI_MODEL_NAME,
                        google_api_key=GOOGLE_API_KEY,
                        temperature=0.2,
                        convert_system_message_to_human=True # Some models work better with this
                    )
                    logger.info("ChatGoogleGenerativeAI Initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize ChatGoogleGenerativeAI. Check API Key and Model Name ({GEMINI_MODEL_NAME}). Error: {e}", exc_info=True)
                    llm = None
        else:
            logger.error(f"Invalid LLM_PROVIDER configured: '{LLM_PROVIDER}'. Use 'groq' or 'gemini'.")
            llm = None

    # --- Load Company Info ---
    if company_text is None:
        company_text = load_company_info()


    # --- Initialize Chain (Only if LLM and company_text are valid) ---
    if chain is None and llm is not None and company_text is not None and not company_text.startswith("Error:"):
        try:
            # Load system prompt from knowledge_base.txt
            system_prompt_text = load_system_prompt()
            
            # Fall back to default if loading fails
            if system_prompt_text is None:
                logger.warning("Could not load system prompt from knowledge_base.txt. Using default prompt.")
                system_prompt_text = f"""
                You ARE the official AI assistant for {COMPANY_NAME}. 
                Your knowledge is based on the 'Company Information' provided.
                Please answer questions about {COMPANY_NAME} in first person using "we" and "our".
                Answer as short as possible.
                """

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt_text),
                ("human", "Company Information:\n{context}\n\nUser Question:\n{user_input}")
            ])

            # Use LCEL Pipe Syntax with StrOutputParser for consistent string output
            chain = prompt_template | llm | StrOutputParser()

            logger.info("LangChain chain initialized successfully using LCEL.")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain chain: {e}", exc_info=True)
            chain = None
    
        

# --- File Handling --- (Keep load_company_info as before)
def load_company_info(file_path=COMPANY_INFO_FILE):
    if not file_path: logger.error("Error: COMPANY_INFO_FILE path not configured."); return "Error: Company information file path not configured."
    try:
        logger.debug(f"Attempting to load company info from: {file_path}")
        if not os.path.exists(os.path.dirname(file_path)): logger.warning(f"Directory for company info file does not exist: {os.path.dirname(file_path)}")
        with open(file_path, "r", encoding="utf-8") as file: content = file.read(); logger.info(f"Successfully loaded company info from {file_path}."); return content
    except FileNotFoundError: logger.error(f"Error: Company information file '{file_path}' not found."); return f"Error: Company information file '{file_path}' not found."
    except IOError as e: logger.error(f"Error reading company info file {file_path}: {e}", exc_info=True); return f"Error reading company info file {file_path}: {e}"
    except Exception as e: logger.error(f"An unexpected error occurred loading company info file {file_path}: {e}", exc_info=True); return f"Error loading company info file {file_path}."


# --- Core Logic --- (Keep retrieve_relevant_text as before)
def retrieve_relevant_text(user_input, company_text_content, max_sentences=5):
    if not company_text_content or company_text_content.startswith("Error:") or not user_input: logger.warning("Could not retrieve relevant text (no input or company text error)."); return "No company information available to search."
    try:
        sentences = [s.strip() for s in company_text_content.split(".") if s.strip()]; input_keywords = set(word.lower() for word in user_input.split() if len(word) > 2)
        matching_sentences = [s for s in sentences if any(keyword in s.lower() for keyword in input_keywords for keyword in input_keywords)]
        relevant_context = ". ".join(s if s.endswith('.') else s + '.' for s in matching_sentences[:max_sentences])
        if relevant_context: logger.debug(f"Retrieved context for '{user_input}': {relevant_context[:100]}..."); return relevant_context
        else: logger.debug(f"No specific context found for '{user_input}' in company details."); return "I do not have specific information on that topic in the provided company details."
    except Exception as e: logger.error(f"Error in retrieve_relevant_text: {e}", exc_info=True); return "Error retrieving relevant text."


def get_ai_response(user_input):
    """Gets the AI response based on user input using the configured LLM."""
    initialize_chatbot() # Ensure initialization is attempted

    # Check if initialization failed
    if llm is None or chain is None:
        logger.error("Cannot generate AI response: LLM or Chain not initialized.")
        provider_name = LLM_PROVIDER.capitalize()
        key_missing = (LLM_PROVIDER == "groq" and not GROQ_API_KEY) or \
                      (LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY)
        reason = f"the {provider_name} API key is missing" if key_missing else \
                 f"the {provider_name} model/chain could not be loaded"
        return f"Sorry, the AI assistant is currently unavailable because {reason}. Please contact support."

    if company_text is None or company_text.startswith("Error:"):
         logger.error("Cannot generate AI response: Company info not available.")
         return f"Sorry, I cannot answer questions right now as the company information is unavailable."

    logger.info(f"Processing user input with {LLM_PROVIDER}: '{user_input}'")
    context = retrieve_relevant_text(user_input, company_text)

    chain_inputs = { "context": context, "user_input": user_input }

    try:
        # Invoke the LCEL chain (prompt | llm | StrOutputParser)
        # StrOutputParser ensures the output is always a string
        ai_response = chain.invoke(chain_inputs)

        if not isinstance(ai_response, str):
             logger.error(f"Unexpected response type from LLM chain (expected string): {type(ai_response)}. Content: {ai_response}")
             ai_response = "Sorry, I received an unexpected response format from the AI."
        else:
            logger.info("Successfully generated AI response.")

        return ai_response

    except Exception as e:
        logger.error(f"Error invoking LLM chain ({LLM_PROVIDER}): {e}", exc_info=True)
        return f"Sorry, I encountered an error processing your request about {COMPANY_NAME}."
