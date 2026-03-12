from redis import Redis
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient, models
from pymongo import MongoClient
from pathlib import Path
from bson import ObjectId
from logging_config import logger
import redis
import gridfs
import tempfile


mongo_client = MongoClient("mongodb://localhost:27017")
mongo_db = mongo_client['rag_db']
fs = gridfs.GridFS(mongo_db)

def check_redis_health(r: redis.Redis):
    try:
        result = r.ping()
        logger.debug("Redis health check successful")
        return result
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        raise

def check_mongo_health():
    try:
        result = mongo_client.admin.command("ping")
        logger.debug("MongoDB health check successful")
        return result
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        raise

def check_qdrant_health():
    try:
        result = QdrantClient(url="http://localhost:6333").get_collections()
        logger.debug("Qdrant health check successful")
        return result
    except Exception as e:
        logger.error(f"Qdrant health check failed: {str(e)}")
        raise

def save_history(r: Redis, session_id, query, response, model, max_history=5):
    """Save query and response summary to Redis session history.
    
    Args:
        r: Redis client instance
        session_id: Unique session identifier
        query: User's query text
        response: LLM's response text
        model: LLM instance for generating summaries
        max_history: Maximum number of history items to keep (default: 5)
    """
    try:
        # use model to create a very short summary of the response to save space in redis
        summary = model.invoke(f"Summarize the following response in one sentence: {response}")
        
        history_key = f"session{session_id}:history"
        # Add to the front of the list
        r.lpush(history_key, f"{query}|||{summary}")
        # Keep only the most recent max_history items
        r.ltrim(history_key, 0, max_history - 1)
        # Set expiration to 30 minutes
        r.expire(history_key, 1800)
        logger.debug(f"History saved for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to save history for session {session_id}: {str(e)}", exc_info=True)
        raise

def get_history(r: Redis, session_id):
    """Retrieve conversation history from Redis for a session.
    
    Args:
        r: Redis client instance
        session_id: Unique session identifier
        
    Returns:
        str: Formatted conversation history or empty string if none exists
    """
    try:
        history_key = f"session{session_id}:history"
        history_list = r.lrange(history_key, 0, -1)

        if not history_list:
            logger.debug(f"No history found for session {session_id}")
            return ""

        history = []
        for item in history_list:
            user, assistant = item.split("|||")
            history.append(f"{user}\n{assistant}")

        logger.debug(f"Retrieved {len(history)} history items for session {session_id}")
        return "\n".join(history)
    except Exception as e:
        logger.error(f"Failed to retrieve history for session {session_id}: {str(e)}", exc_info=True)
        return ""

def replace_t_with_space(list_of_documents):
    """Replace all tab characters with spaces in document content.
    
    Args:
        list_of_documents: List of document objects with page_content attribute
        
    Returns:
        list: Modified documents with tabs replaced by spaces
    """
    for doc in list_of_documents:
        doc.page_content = doc.page_content.replace('\t', ' ')  # Replace tabs with spaces
    return list_of_documents

def create_vector_store(session_id):
    """Initialize and return a Qdrant vector store for document embeddings.
    
    Returns:
        Qdrant: Initialized vector store connected to local Qdrant server
    """
    try:
        logger.debug("Initializing vector store")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.debug("Embeddings model loaded")
        
        # Connect to Qdrant server
        client = QdrantClient(
            url="http://localhost:6333"
        )
        logger.debug("Connected to Qdrant server")

        collection_name = f"rag_docs_{session_id}"
        
        # check if collection exists:
        existing = [c.name for c in client.get_collections().collections]
        
        if collection_name not in existing:
            logger.info(f"Creating new Qdrant collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                )
            )
        else:
            logger.debug(f"Using existing Qdrant collection: {collection_name}")

        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings
        )
        logger.info("Vector store initialized successfully")
        return vectorstore
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
        raise

def encode_pdf(path, chunk_size=1000, chunk_overlap=200):
    """Load PDF and split into chunks for embedding.
    
    Args:
        path: Path to PDF file
        chunk_size: Size of text chunks (default: 1000)
        chunk_overlap: Overlap between consecutive chunks (default: 200)
        
    Returns:
        list: List of document chunks with cleaned content
    """
    try:
        logger.debug(f"Encoding PDF: {path}")
        # Load PDF documents
        loader = PyPDFLoader(path)
        documents = loader.load()
        logger.debug(f"Loaded {len(documents)} pages from PDF")

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
        )
        texts = text_splitter.split_documents(documents)
        cleaned_texts = replace_t_with_space(texts)
        logger.info(f"PDF encoded into {len(cleaned_texts)} chunks")

        return cleaned_texts
    except Exception as e:
        logger.error(f"Failed to encode PDF {path}: {str(e)}", exc_info=True)
        raise

def save_pdf(data, session):
    """Save uploaded PDF to MongoDB GridFS and update session metadata.
    
    Args:
        data: File data from request (with read() and filename attributes)
        session: Session object to update with file metadata
    """
    try:
        logger.debug(f"Saving PDF '{data.filename}' to MongoDB GridFS")
        file_id = fs.put(data.read(), filename=data.filename)
        session.mongo_files[str(file_id)] = {
            "filename": data.filename,
            "embedded": False
        }
        session.save()
        logger.info(f"PDF '{data.filename}' saved with ID: {file_id}")
    except Exception as e:
        logger.error(f"Failed to save PDF '{data.filename}': {str(e)}", exc_info=True)
        raise
    
def update_vector_store(session, vectorstore):
    """Process unembedded PDFs from session and add embeddings to vectorstore.
    
    Args:
        session: Session object containing mongo_files metadata
        vectorstore: Qdrant vector store to update with new embeddings
        
    Returns:
        Qdrant: Updated vector store with new documents
    """
    try:
        logger.info(f"Updating vector store with {len(session.mongo_files)} files")
        docs = []
        
        for fid, meta in session.mongo_files.items():
            
            if meta['embedded']:
                logger.debug(f"File {fid} already embedded, skipping")
                continue
            
            logger.debug(f"Processing file {fid}: {meta['filename']}")
            grid_out = fs.get(ObjectId(fid))
            pdf_bytes = grid_out.read()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)

            texts = encode_pdf(tmp_path)
            
            for t in texts:
                t.metadata['source'] = meta['filename']
                t.metadata['file_id'] = fid
                
            docs.extend(texts)
            tmp_path.unlink()
            meta['embedded'] = True
            logger.info(f"File {fid} processed and marked as embedded")
            
        if docs:
            logger.info(f"Adding {len(docs)} document chunks to vector store")
            vectorstore.add_documents(docs)
            logger.info("Vector store updated successfully")
        else:
            logger.debug("No new documents to add to vector store")
        
        return vectorstore
    except Exception as e:
        logger.error(f"Failed to update vector store: {str(e)}", exc_info=True)
        raise
    
def check_vector_store(vectorstore: QdrantVectorStore):
    """Check if vector store collection exists.
    
    Args:
        vectorstore: Qdrant vector store to check
        
    Returns:
        bool: True if collection exists, False otherwise
    """
    try:
        collections = vectorstore.client.get_collections().collections
        names = [c.name for c in collections]
        
        exists = vectorstore.collection_name in names
        if exists:
            logger.debug(f"Vector store collection '{vectorstore.collection_name}' exists")
        else:
            logger.warning(f"Vector store collection '{vectorstore.collection_name}' not found")
        return exists
    except Exception as e:
        logger.error(f"Failed to check vector store: {str(e)}", exc_info=True)
        return False