import ollama
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel, Field
from utils import create_vector_store, update_vector_store, check_vector_store
from logging_config import logger

class RewriteQuery(BaseModel):
    query: str = Field(..., title='Rewritten Query', description='Rewritten standalone query including relevant history context')
rewrite_prompt = PromptTemplate(
    input_variables=["query", "history"],
    template="""
    You are an assistant that rewrites user queries to be standalone and precise.

    Instructions:
    - Rewrite the latest user query so that it can be understood without conversation history.
    - Include **only the conversation history that is relevant** to clarifying the query.
    - Omit any parts of the history that do not help in rewriting the query.
    - Return your answer in valid JSON with a single field `query`.
    - Do not include any extra text outside the JSON.

    Conversation History (may contain irrelevant parts):
    {history}

    User Query:
    {query}
    
    Return your answer in valid JSON with the key "query" and value is the rewritten query.

    Example output:
    {{"query": "What are the best home remedies for dandruff?"}}
    """
    )

class RetrievalResponse(BaseModel):
    response: str = Field(..., title="Determines if retrieval is necessary", description="Output only 'Yes' or 'No'.")
retrieval_prompt = PromptTemplate(
    input_variables=["query"],
    template="""
    Given the query '{query}', determine if retrieval is necessary.

    Return your answer in valid JSON with the key "response" and value "Yes" or "No".

    Example:
    {{"response": "Yes"}}
    """
)

class RelevanceResponse(BaseModel):
    response: str = Field(..., title="Determines if context is relevant", description="Output only 'Relevant' or 'Irrelevant'.")
relevance_prompt = PromptTemplate(
    input_variables=["query", "context"],
    template="""
    Given the query '{query}' and the context '{context}', determine if the context is relevant. 
    
    Return your answer in valid JSON with the key "response" and value 'Relevant' or 'Irrelevant'.
    
    Example:
    {{"response": "Relevant"}}
    
    """
)

class GenerationResponse(BaseModel):
    response: str = Field(..., title="Generated response", description="The generated response.")
generation_prompt = PromptTemplate(
    input_variables=["query", "context"],
    template="""
    You are an assistant that answers a user's query using the provided context.

    Query:
    {query}

    Context:
    {context}

    Instructions:
    - Generate a response that is precise, concise, and directly answers the query.
    - Use complete sentences.
    - If the context does not provide enough information, respond: "I don't have enough information to answer that."
    - **Return your answer in valid JSON with a single key "response".**
    - Do not include any additional text outside the JSON.
    
    Return your answer in valid JSON with the key "response" and value as the generated response.

    Example:
    {{"response": "I don't have enough information to answer that."}}
    """
)

class SupportResponse(BaseModel):
    response: str = Field(..., title="Determines if response is supported", description="Output 'Fully supported', 'Partially supported', or 'No support'.")
support_prompt = PromptTemplate(
    input_variables=["response", "context"],
    template="""
    Given the response '{response}' and the context '{context}', determine if the response is supported by the context.
    
    Return your answer in valid JSON with the key "response" and value 'Fully supported', 'Partially supported', or 'No support'.
    
    Example:
    {{"response": "Fully supported"}}
    """
)

class UtilityResponse(BaseModel):
    response: int = Field(..., title="Utility rating", description="Rate the utility of the response from 1 to 5.")
utility_prompt = PromptTemplate(
    input_variables=["query", "response"],
    template="""
    Given the query '{query}' and the response '{response}', rate the utility of the response from 1 to 5.
    
    Return your answer in valid JSON with the key "response" and value in the range [1,5]. Do not add any extra text.
    
    Example:
    {{"response": "5"}}
    """
)

class Chains(BaseModel):
    rewrite: RunnableSerializable
    retrieval: RunnableSerializable
    relevance: RunnableSerializable
    generation: RunnableSerializable
    support: RunnableSerializable
    utility: RunnableSerializable

def create_chains(llm: ChatOllama):
    """Create and return all LLM chains for the RAG pipeline.
    
    Args:
        llm: Ollama language model instance
        
    Returns:
        Chains: Container with all configured chains
    """
    logger.debug("Creating RAG pipeline chains")
    rewrite = rewrite_prompt | llm.with_structured_output(RewriteQuery, method="json_mode")
    retrieval = retrieval_prompt | llm.with_structured_output(RetrievalResponse, method="json_mode")
    relevance = relevance_prompt | llm.with_structured_output(RelevanceResponse, method="json_mode")
    generation = generation_prompt | llm.with_structured_output(GenerationResponse, method="json_mode")
    support = support_prompt | llm.with_structured_output(SupportResponse, method="json_mode")
    utility = utility_prompt | llm.with_structured_output(UtilityResponse, method="json_mode")
    
    logger.info("All RAG chains created successfully")
    return Chains(
        rewrite=rewrite,
        retrieval=retrieval,
        relevance=relevance,
        generation=generation,
        support=support,
        utility=utility
    )
    
class SelfRAG:
    """Self-Reflective Retrieval-Augmented Generation pipeline.
    
    Implements a RAG system with self-reflection capabilities for query rewriting,
    document retrieval, relevance evaluation, response generation, and quality assessment.
    """
    def __init__(self):
        """Initialize the SelfRAG system with vectorstore."""
        self.session = None
        self.llm = None
        self.vectorstores = {}
        self.chains = None
        logger.debug("SelfRAG instance initialized")
    
    def add_session(self, session_id):
        """Attach a user session to the RAG pipeline.
        
        Args:
            session: Session object containing user data and file references
        """
        logger.info("Adding session to RAG pipeline")
        self.vectorstores[session_id] = create_vector_store(session_id)
        logger.debug("Vector store created for session")
        
    def create_model(self, api_key, model):
        """Initialize the LLM and create processing chains.
        
        Args:
            api_key: API key for authentication with the LLM provider
        """
        try:
            logger.info(f"Initializing LLM model: {model}")
            import os
            os.environ["OLLAMA_API_KEY"] = api_key
            model = ChatOllama(model=model,
                base_url="https://ollama.com",)
            
            self.llm = model
            self.chains = create_chains(self.llm)
            logger.info("LLM model and chains created successfully")
        except Exception as e:
            logger.error(f"Failed to create LLM model: {str(e)}", exc_info=True)
            raise
        
    def get_updated_vector_store(self, session):
        """Update vectorstore with newly embedded documents from session.
        
        Args:
            session: Session object containing session_id and mongo_files
        
        Returns:
            Vectorstore with updated embeddings
        """
        try:
            # Initialize vector store if not already done
            vectorstore = self.vectorstores[session.session_id]
            if vectorstore is None:
                logger.warning("Vector store not initialized, initializing now")
                self.vectorstores[session.session_id] = create_vector_store(session.session_id)
            
            logger.debug("Updating vector store with new documents")
            self.vectorstores[session.session_id] = update_vector_store(session, vectorstore)
            return self.vectorstores
        except Exception as e:
            logger.error(f"Failed to update vector store: {str(e)}", exc_info=True)
            raise
        
    def run(self, query: str, history: str, session, top_k: int=3):
        """Execute the RAG pipeline with self-reflection.
        
        Process user query through rewriting, retrieval, relevance evaluation,
        response generation, and quality assessment steps.
        
        Args:
            query: User's input query
            history: Conversation history context
            session: Session object containing session_id and mongo_files
            top_k: Number of top documents to retrieve (default: 3)
            
        Returns:
            str: Best generated response based on support and utility scores
        """
        try:
            logger.info("Starting RAG pipeline execution")
            vectorstore = self.get_updated_vector_store(session)[session.session_id]
            has_docs = check_vector_store(vectorstore)
            chains = self.chains if self.chains else create_chains(self.llm)
            #print(type(chains))
            
            # Step 1: rewrite query using the recent chat history
            logger.debug("Step 1: Rewriting query based on history")
            input_data = {"query" : query, "history" : history} 
            new_query = chains.rewrite.invoke(input_data).query
            logger.debug(f"Rewritten query: {new_query}")
            
            # Step 2: Check of vector store has any embeddings
            logger.debug("Step 2: Checking vector store for documents")
            count = 0
            if has_docs:
                count = vectorstore.client.count(
                    collection_name=vectorstore.collection_name
                ).count
            logger.debug(f"Vector store contains {count} documents")
            
            if count > 0:
            
                # Step 3: Determine if retrival is necessary
                logger.debug("Step 3: Determining if retrieval is necessary")
                input_data = {"query" : new_query}
                retrieval_decision = chains.retrieval.invoke(input_data).response.strip().lower()
                logger.debug(f"Retrieval decision: {retrieval_decision}")
                
                if retrieval_decision == 'yes':
                    # Step 4: Retrieve relevant documents
                    logger.debug(f"Step 4: Retrieving top {top_k} documents")
                    docs = vectorstore.similarity_search(new_query, top_k)
                    logger.debug(f"Retrieved {len(docs)} documents")
                    contexts = [doc.page_content for doc in docs]
                    
                    # Step 5: Evaluate relevance of teh retrived documents
                    logger.debug("Step 5: Evaluating relevance of retrieved documents")
                    relevant_context = []
                    for i, context in enumerate(contexts):
                        input_data = {"query": new_query, "context" : context}
                        relevance = chains.relevance.invoke(input_data).response.strip().lower()
                        logger.debug(f"Document {i+1} relevance: {relevance}")
                        
                        if relevance == 'relevant':
                            relevant_context.append(context)
                    
                    logger.info(f"Found {len(relevant_context)} relevant documents")
                            
                    # if no relevant contexts found, generate answer directly
                    if not relevant_context:
                        logger.info("No relevant context found, generating answer without retrieval")
                        input_data = {"query": new_query, "context": "No relevant context found."}
                        return chains.generation.invoke(input_data).response
                    
                    # Step 6: Generate response using relevant contexts
                    logger.debug("Step 6: Generating responses using relevant contexts")
                    responses=[]
                    for i, context in enumerate(relevant_context):
                        input_data = {"query":new_query, "context": context}
                        response = chains.generation.invoke(input_data).response
                        
                        # Step 7: Assess Support
                        input_data = {"response": response, "context":context}
                        support = chains.support.invoke(input_data).response.strip().lower()
                        logger.debug(f"Response {i+1} support level: {support}")
                        
                        # Step 8: Evaluate Utility
                        input_data = {"query":query, "response":response}
                        utility = int(chains.utility.invoke(input_data).response)
                        logger.debug(f"Response {i+1} utility score: {utility}/5")
                        
                        responses.append((response, support, utility))
                    
                    best_response = max(responses, key=lambda x: (x[1] == 'fully supported', x[2]))
                    logger.info(f"Selected best response with support '{best_response[1]}' and utility {best_response[2]}")
                    return best_response[0]
                else:
                    logger.info("Retrieval not necessary, generating direct answer")
                    input_data = {"query": new_query, "context": "No retrieval necessary."}
                    return chains.generation.invoke(input_data).response
            else:
                # normal chat with llm without retrirve
                logger.info("No documents in vector store, using default LLM chat")
                prompt = PromptTemplate(
                    input_variables=['query'],
                    template="""
                        GIven the question {query}, provide a very short and precise answer.
                    """
                )
                default_chain = prompt | self.llm
                return default_chain.invoke({'query' : new_query}).content
                
        except Exception as e:
            logger.error(f"Error during RAG pipeline execution: {str(e)}", exc_info=True)
            raise
        

    