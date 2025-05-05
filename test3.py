from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from ragas import evaluate
from ragas.metrics import ResponseRelevancy, LLMContextRecall, Faithfulness, FactualCorrectness
from ragas.llms import LangchainLLMWrapper
from ragas import SingleTurnSample, EvaluationDataset
from datasets import Dataset
import os
import numpy as np
import pandas as pd
import traceback

# Set a dummy OpenAI key to prevent initialization errors in RAGAS
os.environ["OPENAI_API_KEY"] = "dummy-key"

# Load environment variables
load_dotenv()

# Make sure GROQ API key is available
if "GROQ_API_KEY" not in os.environ:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please add it to your .env file.")

# Create a simple RAG implementation
class RAG:
    def __init__(self):
        # Initialize the embedding model
        self.embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        # Initialize the LLM for generation with Groq API key
        self.llm = ChatGroq(
            api_key=os.environ["GROQ_API_KEY"],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_retries=2,
        )
        self.documents = []
        self.embeddings = []
        
    def load_documents(self, documents):
        self.documents = documents
        # Create embeddings for all documents
        self.embeddings = self.embedding_model.encode(documents)
        
    def get_most_relevant_docs(self, query):
        # Create embedding for the query
        query_embedding = self.embedding_model.encode([query])[0]
        
        # Calculate similarity between query and all documents
        similarities = []
        for doc_embedding in self.embeddings:
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            similarities.append(similarity)
        
        # Get index of the most relevant document
        most_relevant_idx = np.argmax(similarities)
        
        # Return the most relevant document
        return self.documents[most_relevant_idx]
    
    def generate_answer(self, query, context):
        # Format the prompt with the query and context
        prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        
        # Generate response using the LLM
        response = self.llm.invoke(prompt)

        # Extract the content from the AIMessage object
        if hasattr(response, 'content'):
            return response.content
        else:
            return str(response)

if __name__ == "__main__":
    # Sample documents related to AMD
    sample_docs = [
        "Advanced Micro Devices, Inc. (AMD) is an American multinational semiconductor company based in Santa Clara, California.",
        "AMD develops computer processors and related technologies for business and consumer markets.",
        "AMD's main products include microprocessors, motherboard chipsets, embedded processors, graphics processors, and FPGAs.",
        "AMD was founded on May 1, 1969, by Jerry Sanders, along with seven of his colleagues from Fairchild Semiconductor.",
        "ADVANCED MICRO DEVICES, INC. is the full legal name of AMD, a global semiconductor company."
    ]

    # Initialize evaluator LLM with explicit API key
    evaluator_groq = ChatGroq(
        api_key=os.environ["GROQ_API_KEY"],
        model="llama-3.1-8b-instant",
        temperature=0.0,
        max_retries=2,
    )
    
    # Wrap with LangchainLLMWrapper for RAGAS compatibility
    evaluator_llm = LangchainLLMWrapper(evaluator_groq)

    # Initialize RAG instance before using it
    rag = RAG()
    
    # Load documents
    rag.load_documents(sample_docs)

    # Your specific query, ground truth, and AI response
    sample_queries = [
        "What is the full name of the AMD?",
        "Which all AMD documents do you have access to?",
        "What is the address of AMD's headquarters?",
        "Who are the key management team members of AMD as of the latest filing?",
        "What is the total number of patents that AMD has as of the latest reporting?",
        "Give a brief history of AMD.",
        "What are the main products of AMD? Give a brief description.",
        "What are the main revenue segments of AMD at the end of 2023?",
        "Who are the main competitors of AMD as of 2023?",
        "What are the major risk factors for AMD?",
        "What are the acquisitions AMD has done over the last 5 years?",
        "Is AMD operating in a crowded market?",
        "What is AMD's market share in its major revenue segment?",
        " How is the corporate governance at the company with respect to disclosures, independent directors as in 2023?"
    ]

    # Ground truth responses
    expected_responses = [
        "ADVANCED MICRO DEVICES, INC.",
        "10K reports of AMD from 2014 till 2023",
        "2485 Augustine Drive, Santa Clara, California 95054, United States",
        """Below are the key members of the management team:
        - President and CEO, Director: Lisa T. Su
        - Executive Vice President, Chief Financial Officer and Treasurer: Jean Hu
        - Corporate Vice President, Chief Accounting Officer: Darla Smith
        """,
        "As per the company's 10K FY2023: they had approximately 7,500 patents in the United States and approximately 2,000 patent applications pending in the United States; Including United States and foreign matters, they have approximately 18,500 patent matters worldwide consisting of approximately 12,800 issued patents and 5,600 patent applications pending",
        "AMD, a global semiconductor company, was incorporated in 1969 as a Silicon Valley start-up with dozens of employees focused on leading-edge semiconductor products, and became public in 1972. Today, they have grown into a global company achieving many important industry firsts along the way. They develop high-performance and adaptive computing to solve some of the world's toughest and most interesting challenges.",
        "AMD's products include x86 microprocessors (CPUs) and graphics processing units (GPUs), as standalone devices or as incorporated into accelerated processing units (APUs), chipsets, data center and professional GPUs, embedded processors, semi-custom System-on-Chip(SoC) products, microprocessor and SoC development services and technology, data processing units (DPUs), Field Programmable Gate Arrays (FPGAs),System on Modules (SOMs), Smart Network Interface Cards (SmartNICs), AI Accelerators and Adaptive SoC products.",
        """Major revenue segments of AMD:
        - Data Center: 29% of net revenue
        - Client: 21% of net revenue
        - Gaming: 27% of net revenue
        - Embedded: 23% of net revenue""",
        """Segment wise competitors:
        - Data Center: Nvidia and Intel
        - Client Segment: Intel
        - Gaming Segment: Nvidia, Intel
        - Embedded Segment: Intel, Lattice Semiconductor and Microsemi Corporation (Microsemi,acquired by Microchip), from ASSP vendors such as Broadcom Corporation, Marvell Technology Group, Analog Devices, Texas Instruments and NXP Semiconductors, and from NVIDIA""",
        """Major risk factors for AMD:
        - Intel Corporation's dominance of the microprocessor market and its aggressive business practices may limit AMD's ability to compete effectively on a level playing field
        - Cyclicity of the semiconductor industry, and the fluctuation of demand for products
        - Success for AMD is dependent upon its ability to introduce products on a timely basis with features and performance levels that provide value to their customers while supporting and coinciding with significant industry transitions; so consistent innovation and product upgradation is required
        - AMD relies on third parties to manufacture its products, and if they are unable to do so on a timely basis in sufficient quantities and using competitive technologies, AMD's business could be materially adversely affected
        - If AMD loses Microsoft Corporation's support for their products or other software vendors do not design and develop software to run on their products, their ability to sell their products could be materially adversely affected
        - Government actions and regulations such as export regulations, tariffs, and trade protection measures may limit AMD's ability to export our products to certain customers
        """,
        """ - October 2023, they acquired Nod Inc, an open AI software company
            - August 2023, AMD acquired Mipsology SAS, an AI software company
            - May 2022, AMD acquired Pensando for, a next-generation distributed computing company
            - February 2022, AMD acquired Xilinx, a provider of adaptive computing solutions""",
        """AMD operates in a highly competitive market, and the company expects the competition to continue to be intense due to rapid technological changes, frequent product introductions by its competitors or new competitors of products that may provide better performance or experience or that may include additional features that render AMD's products comparatively less competitive.""",
        """Industry size/market size data is not available, however, as for AMD's net revenue for financial year 2023, below is how its segments contributed to its total revenue of $22,680 Mn:
        - Data Center: 29%
        - Client: 21%
        - Gaming: 27%
        - Embedded: 23%""",
        "Corporate Governance Principles of the company are posted on an external link, and its not available in the 10K reports."
    ]

    # AI Responses (predefined)
    AI_Responses = [
        "Based on general knowledge, I believe the user is referring to Advanced Micro Devices. However, I would like to acknowledge that without specific documents, I may not have the most accurate or up-to-date information. Nevertheless, Advanced Micro Devices is a well-known global semiconductor company that specializes in the design and manufacture of microprocessors, graphics processing units, and other semiconductor products.",
        """As a business analyst, I have access to AMD's publicly available documents and company reports. Specifically, I have access to:
        1. AMD's annual reports (10-K) and quarterly reports (10-Q) filed with the Securities and Exchange Commission (SEC).
        2. AMD's investor relations website, which provides information on company performance, financials, and product updates.
        3. AMD's official press releases and news announcements.
        Please note that I do not have access to proprietary or confidential documents. If you require specific or detailed information, I would be happy to provide general guidance or suggest alternative sources where you may be able to find the information you need.""",
        """Based on my general knowledge, Advanced Micro Devices (AMD) is a multinational semiconductor company. While I don't have specific documents to reference, I can confirm that AMD's headquarters is typically associated with the following address: 
        One AMD Place, 
        Sunnyvale, CA 94085, USA.
        Please note that this information may be subject to change, and I recommend verifying it through AMD's official website or other reliable sources for the most up-to-date information.""",
        """While I don't have access to the latest filing of AMD, I can provide some general information on the company's management structure. 
        AMD is a publicly traded company, and as such, its management team is typically disclosed in its annual reports (Form 10-K) and quarterly reports (Form 10-Q). However, without access to the most recent filing, I can only provide information from publicly available sources.
        Based on my general knowledge, some key management team members of AMD have included:
        - Dr. Lisa Su - President and Chief Executive Officer
        - Devinder Kumar - Chief Financial Officer
        - Mark Papermaster - Senior Vice President and Chief Technology Officer
        Please note that the management team composition may change over time, and this information may not reflect the current team members. I recommend checking the company's most recent filings with the Securities and Exchange Commission (SEC) for the most up-to-date information.""",
        """While I don't have access to the most up-to-date information on AMD's patent portfolio, I can provide some general insight. AMD is a technology company that has a significant research and development presence, particularly in the fields of semiconductors, computer hardware, and software.
        As of my knowledge cutoff, AMD has been actively pursuing innovation and has filed numerous patent applications over the years. However, I couldn't find a specific, publicly available source that reports the exact number of patents held by AMD as of the latest reporting.
        For the most accurate and current information, I would recommend checking AMD's official investor relations website or recent SEC filings. These sources may provide a more comprehensive overview of the company's intellectual property portfolio, including the number of patents held.""",
        """Based on general knowledge and industry understanding, I can provide a brief overview of AMD's history. However, please note that my information may not be exhaustive or up-to-date, and I may not have access to the most recent or detailed records.
        Advanced Micro Devices (AMD) was founded in 1969 by Jerry Sanders. Initially, the company focused on developing calculators and other semiconductor products. In the late 1970s, AMD began to shift its focus towards microprocessors, releasing its first x86 processor in 1978, a version of the Intel 8086.
        Throughout the 1990s and 2000s, AMD faced intense competition from Intel. However, the company responded by innovating and expanding its product line, introducing multi-core processors, and acquiring several companies, including ATI Technologies in 2006.
        In recent years, AMD has experienced significant growth and resurgence, driven by the success of its Ryzen and EPYC processors, as well as the acquisition of Xilinx in 2021. Today, AMD is a major player in the semiconductor industry, competing with Intel in the market for central processing units (CPUs) and graphics processing units (GPUs).""",
        """Based on my general knowledge of AMD, I can provide a brief overview of their main products. However, I must note that this information may not be up-to-date or exhaustive due to the limitations of available data.
        AMD is a leading technology company that designs and manufactures various semiconductor products. Their main product lines include:
        1. **CPUs (Central Processing Units)**: AMD offers a range of processors for desktops, laptops, and servers, including their Ryzen and EPYC lines, which compete with Intel's offerings.
        2. **GPUs (Graphics Processing Units)**: AMD's Radeon graphics cards are designed for gaming, professional graphics, and machine learning applications.
        3. **APUs (Accelerated Processing Units)**: AMD's APUs integrate a CPU and GPU on a single chip, offering a balance of processing and graphics performance for various applications.
        4. **Embedded Solutions**: AMD provides a range of embedded processors for IoT, automotive, and other specialized applications.
        Please note that this is a general summary, and AMD's product portfolio may have evolved since my knowledge cutoff.""",
        """"Based on publicly available information, I can provide an overview of AMD's revenue segments. However, please note that I do not have specific documents from 2023 to reference, and this response should be considered an educated estimate.
        AMD's main revenue segments are typically categorized into three main areas:
        1. Computing and Graphics (CG): This segment includes revenue from desktop and mobile processors, as well as graphics processing units (GPUs) for gaming and professional applications.
        2. Enterprise, Embedded and Semi-Custom (EESC): This segment includes revenue from server and datacenter processors, embedded processors for IoT devices, and custom SoCs for gaming consoles and other specialized applications.
        3. Gaming (formerly Gaming and Visual Solutions): Although the name may have changed, AMD's revenue from gaming GPUs remains a significant contributor to their overall revenue.
        Please note that these segments may not be mutually exclusive, and revenue may overlap across categories. I would recommend consulting AMD's official financial reports or news releases for more accurate and up-to-date information."
        """,
        """As of 2023, AMD's main competitors in the CPU and GPU markets are generally understood to be Intel and NVIDIA, respectively. However, it's essential to note that market dynamics can shift rapidly, and there may be other emerging competitors in specific segments.
        In the CPU market, Intel is AMD's primary rival, with both companies vying for market share in the desktop, laptop, and server segments.
        In the GPU market, NVIDIA is the primary competitor to AMD, with both companies competing in the discrete graphics card and professional graphics markets.
        Please note that this information is based on general knowledge and industry trends, rather than specific documents or up-to-date data.""",
        """Based on general knowledge and industry trends, I would like to acknowledge that I don't have access to specific documents or information about Advanced Micro Devices (AMD). However, I can provide some general insights on potential risk factors that may be applicable to the company.
        Some potential risk factors for AMD could include:
        1. Competition from Intel**: As a major player in the semiconductor industry, AMD faces intense competition from Intel, which could impact revenue and market share.
        2. Volatile demand for semiconductors**: The demand for semiconductors can be highly cyclical and subject to economic fluctuations, which may impact AMD's revenue and profitability.
        3. Supply chain disruptions**: AMD relies on complex global supply chains, which can be vulnerable to disruptions such as natural disasters, trade tensions, or pandemic-related lockdowns.
        4. Intellectual property disputes**: The semiconductor industry is known for intellectual property disputes, which could potentially impact AMD's ability to innovate and compete.
        Please note that these risk factors are speculative and may not be accurate or comprehensive. I would recommend consulting AMD's official reports and financial statements for a more detailed understanding of the company's risk profile.""",
        """Based on my general knowledge, AMD (Advanced Micro Devices) has made several acquisitions over the past 5 years. However, I must note that without specific documents or official statements from AMD, I can only provide a limited and potentially incomplete overview of their transactions.
        From publicly available information, some notable acquisitions by AMD include:
        * Xilinx in 2021 - a leading provider of adaptive and programmable semiconductor solutions.
        * Wibrain in 2011 - a mobile processor developer (Note: This is outside the 5-year time frame, but might be notable still)
        Please note that this list might not be exhaustive, and AMD may have made other acquisitions not publicly disclosed or outside the specified time frame. I recommend verifying this information through official sources or AMD's investor relations website for the most accurate and up-to-date information.""",
        """While I don't have direct access to AMD's market analysis documents, I can provide some general insights. The microprocessor market is indeed competitive, with key players including AMD, Intel, and NVIDIA (in the GPU segment). Additionally, the growing presence of ARM-based processors and other emerging players like Apple's M-series chips may further intensify competition.
        AMD, however, has been successful in gaining market share in recent years, particularly in the gaming and server markets. Their Ryzen and EPYC product lines have been well-received by customers and critics alike. Nonetheless, AMD will need to continue innovating and differentiating their products to maintain a competitive edge in the market.""",
        """AMD (Advanced Micro Devices) is a multinational semiconductor company with a diverse portfolio of products, including CPUs, GPUs, and APU (Accelerated Processing Unit) solutions. While I don't have specific documents to reference, based on publicly available information, AMD's major revenue segments include Client Computing, Gaming, Datacenter, and Embedded.
        Historically, AMD has been a significant player in the CPU market, with a notable market share in the desktop and laptop segments. In the GPU market, AMD competes with NVIDIA, and while market share figures are not publicly disclosed, AMD's Radeon GPUs are widely used in gaming and professional graphics applications.
        In terms of market share, according to a report from 2022 by Jon Peddie Research, AMD held around 29% market share in the discrete GPU market, while NVIDIA held around 71%. However, please note that this information may not reflect the current market situation.
        In the CPU market, AMD has made significant gains in recent years, particularly in the server market, where it competes with Intel. However, market share figures for the CPU segment are not readily available.
        I would like to emphasize that these figures are based on publicly available information and may not reflect the company's current market position. For more accurate and up-to-date information, I would recommend consulting AMD's official financial reports or industry reports from reputable sources.""",
        """Based on general knowledge and publicly available information, I can provide some insights on AMD's corporate governance as of 2023. However, I want to emphasize that my answer may not be exhaustive or up-to-date, and I encourage verifying this information with AMD's official resources or regulatory filings.
        AMD, being a publicly-traded company, is subject to certain regulatory requirements and guidelines. As of my knowledge cutoff, AMD has a board of directors that oversees the company's strategy and operations. The board typically consists of a mix of executive and non-executive directors, including independent directors who are not affiliated with the company or its management.
        Regarding disclosures, AMD is required to comply with the Securities and Exchange Commission (SEC) regulations, including filing annual reports (10-K) and quarterly reports (10-Q). These reports provide a comprehensive overview of the company's financial performance, operations, and governance.
        As for independent directors, I couldn't find specific information on the exact number or composition of AMD's board as of 2023. However, it is common for publicly-traded companies to have a majority of independent directors to ensure a level of objectivity and oversight."""

    ]

    # Retrieve relevant documents for each query
    print("\nRetrieving relevant documents...")
    retrieved_docs_list = []
    for query in sample_queries:
        relevant_doc = rag.get_most_relevant_docs(query)
        retrieved_docs_list.append(relevant_doc)
        print(f"Query: {query}")
        print(f"Retrieved document: {relevant_doc[:100]}...")
        
    # Create RAGAS evaluation dataset
    print("\nCreating evaluation dataset...")
    # Use from_dict instead of from_list to ensure proper formatting
    evaluation_data_dict = {
        "question": sample_queries,
        "answer": AI_Responses,
        "contexts": [[doc] for doc in retrieved_docs_list],
        "reference": expected_responses
    }

    # Create dataset using Dataset from huggingface datasets
    dataset_hf = Dataset.from_dict(evaluation_data_dict)

    # Initialize metrics with explicit configurations
    print("\nInitializing metrics...")

    # Use HuggingFace embeddings for all metrics
    hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    
    metrics = [
        ResponseRelevancy(llm=evaluator_llm, embeddings=hf_embeddings), 
        LLMContextRecall(llm=evaluator_llm), 
        Faithfulness(llm=evaluator_llm), 
        FactualCorrectness(llm=evaluator_llm)
    ]

    # Run evaluation
    print("\nRunning evaluation...")
    try:
        result = evaluate(
            dataset=dataset_hf,
            metrics=metrics,
            llm=evaluator_llm,
            raise_exceptions=False
        )
        
        # Convert to pandas DataFrame for better display
        result_df = result.to_pandas()
        
        # Display results
        print("\n===== EVALUATION RESULTS =====")
        print(result_df)


        # Save results to Excel
        excel_filename = "ragas_evaluation_results.xlsx"
        result_df.to_excel(excel_filename, index=True)
        print(f"\nResults saved to {excel_filename}")
        
        
        # Print individual metrics
        print("\n===== DETAILED METRICS =====")
        for metric_name in result_df.columns:
            if metric_name != 'index' and metric_name not in ['user_input', 'retrieved_contexts', 'response', 'reference']:
                try:
                    avg_score = result_df[metric_name].mean()
                    print(f"{metric_name}: {avg_score}")
                except TypeError:
                    # Handle case where the metric is not numeric
                    print(f"{metric_name}: Non-numeric values (see CSV for details)")
                
    except Exception as e:
        print(f"Error during evaluation: {e}")
        traceback.print_exc()
        
    # Print detailed output
    print("\n===== DETAILED EVALUATION OUTPUT =====")
    for i in range(len(sample_queries)):
        print(f"\nQuery {i+1}: {sample_queries[i]}")
        print(f"Retrieved Context: {retrieved_docs_list[i][:150]}...")  # Show first 150 chars
        print(f"AI Response: {AI_Responses[i][:150]}...")  # Show first 150 chars
        print(f"Ground Truth: {expected_responses[i][:150]}...")  # Show first 150 chars
        
        # Print individual metric scores if available
        if 'result_df' in locals():
            print("Metric Scores:")
            for metric_name in result_df.columns:
                if metric_name != 'index' and metric_name not in ['user_input', 'retrieved_contexts', 'response', 'reference']:
                    try:
                        value = result_df.iloc[i][metric_name]
                        if isinstance(value, (int, float)):
                            print(f"  - {metric_name}: {value:.4f}")
                        else:
                            print(f"  - {metric_name}: {value}")
                    except Exception as e:
                        print(f"  - {metric_name}: Error displaying value ({e})")