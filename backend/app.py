from flask import Flask, request, jsonify, make_response
from api_validation import validate_api
from utils import save_history, get_history, save_pdf, check_mongo_health, check_qdrant_health, check_redis_health
from session import Session, get_redis_obj
from model import SelfRAG
from logging_config import logger

app = Flask(__name__)
engine = SelfRAG()
r = get_redis_obj()
logger.info("Flask app initialized with SelfRAG engine")
    
@app.route("/health", methods=["GET"])
def health():
    logger.info("Health check endpoint called")
    status = {"redis" : False, "mongo" : False, "qdrant" : False}
    
    # check redis server
    try:
        check_redis_health(r)
        status["redis"] = True
        logger.debug("Redis health check passed")
    except Exception as e:
        status["redis"] = False
        logger.warning(f"Redis health check failed: {str(e)}")
        
    # check mongo db
    try:
        check_mongo_health()
        status["mongo"] = True
        logger.debug("MongoDB health check passed")
    except Exception as e:
        status["mongo"] = False
        logger.warning(f"MongoDB health check failed: {str(e)}")
        
    # check qdrant 
    try:
        check_qdrant_health()
        status["qdrant"] = True
        logger.debug("Qdrant health check passed")
    except Exception as e:
        status["qdrant"] = False
        logger.warning(f"Qdrant health check failed: {str(e)}")
        
    health = all(status.values())
    if health:
        logger.info("All services healthy")
        return jsonify({"status" : "ok"})
    else:
        logger.error(f"Health check failed. Status: {status}")
        return jsonify({"status" : "down", **status})
        

@app.route("/load", methods=["GET"])
def load_page():
    """Initialize a new user session.
    
    Creates a new session, stores it in Redis, and attaches it to the RAG engine.
    
    Returns:
        JSON with success status and session_id, or error message
    """
    logger.info("Loading new session")
    # create a new session
    try:
        session_obj = Session.create_new()
        logger.debug(f"New session created with ID: {session_obj.session_id}")
        
        session_obj.save()  # store in Redis
        logger.debug(f"Session {session_obj.session_id} saved to Redis")
        
        engine.add_session(session_obj.session_id)
        logger.info(f"Session {session_obj.session_id} initialized successfully")
        
        response = make_response(jsonify({
            "status": "success",
            "session_id": session_obj.session_id
        }))
        
        response.set_cookie(
            "session_id",
            session_obj.session_id,
            httponly=True,
            samesite="Lax"
        )

        return response
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        return jsonify({
            "status": "failed",
            "message": str(e)
        })
    
@app.route('/new', methods=["GET"])
def reset():
    """Clear conversation history for the current session.
    
    Deletes all saved history entries from Redis for the active session.
    
    Returns:
        JSON with success status
    """
    try:
        session_id = request.cookies.get("session_id")
        logger.debug(f"Resetting session {session_id}")
        
        # get session
        session = Session.load(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for reset")
            return jsonify({"status": "failed", "message": "Session not found"})
        
        # clear session history
        if session.session_id:
            r.delete(f"session{session.session_id}:history")
            logger.info(f"Session {session.session_id} history cleared")
        
        return jsonify({"status" : "success"})
    except Exception as e:
        logger.error(f"Failed to reset session: {str(e)}", exc_info=True)
        return jsonify({"status": "failed", "message": str(e)})

@app.route('/api', methods=["POST"])
def set_api_key():
    """Validate and store API key for the session.
    
    Validates the provided API key and initializes the LLM if valid.
    
    Returns:
        JSON with success status or error message
    """
    try:
        data = request.json
        model = data.get("model")
        print(type(model))
        session_id = request.cookies.get("session_id")
        logger.debug(f"API key validation requested for session {session_id}")
        
        session = Session.load(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for API key setup")
            return jsonify({"status": "failed", "message": "Session not found"})

        api_key = data['api_key']
        msg, valid = validate_api(api_key)

        if not valid:
            logger.warning(f"Invalid API key provided for session {session_id}: {msg}")
            return jsonify({"status" : "failed", "message" : msg})

        session.api_key = api_key
        session.model = model
        session.save()
        logger.debug(f"API key saved for session {session_id}")
        logger.debug(f"Model {model} saved for session {session_id}")
        
        engine.create_model(api_key, model)
        #print(type(engine.llm))
        logger.info(f"LLM model initialized successfully for session {session_id}")

        return jsonify({"status" : "success", "message" : "API Key Recieved and Saved."})
    except Exception as e:
        logger.error(f"Error setting API key: {str(e)}", exc_info=True)
        return jsonify({"status": "failed", "message": str(e)})
    
@app.route('/chat', methods=["POST"])
def chat_with_ai():
    """Process user query through RAG pipeline and save response.
    
    Retrieves conversation history, runs query through SelfRAG, saves the
    interaction to Redis, and returns the generated response.
    
    Request JSON should contain 'query' field.
    
    Returns:
        JSON with success status and generated response, or error message
    """
    try:
        data = request.json
        session_id = request.cookies.get("session_id")
        logger.debug(f"Chat request for session {session_id}")
        
        session = Session.load(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for chat")
            return jsonify({"status": "failed", "message": "Session not found"})
        
        api_key = session.api_key
        if not api_key:
            logger.warning(f"No API key set for session {session_id}")
            return jsonify({"status" : "failed",
                        "message" : "API Key Expired or Not Found. Please set your API Key first."})

        query = data.get('query', '')
        logger.debug(f"Query received: {query[:100]}..." if len(query) > 100 else f"Query received: {query}")

        if query:
            history = get_history(r, session.session_id)
            logger.debug(f"Retrieved conversation history for session {session_id}")
            
            logger.info(f"Processing query for session {session_id}")
            response = engine.run(query, history, session)
            
            save_history(r, session.session_id, query, response, engine.llm)
            logger.debug(f"Chat history saved for session {session_id}")
            
            logger.info(f"Query processed successfully for session {session_id}")
            return jsonify({"status" : "success",
                            "response" : response})
        else:
            logger.warning(f"Empty query received for session {session_id}")
            return jsonify({"status": "failed", "message": "Query cannot be empty"})
            
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        return jsonify({
            "status": "failed",
            "message" : str(e)
        })
        
@app.route('/upload', methods=["POST"])
def upload():
    """Handle PDF file upload and storage for document retrieval.
    
    Saves uploaded PDF to MongoDB GridFS and marks it for processing.
    Files are embedded and added to vectorstore on next query.
    
    Returns:
        JSON with success status or error message
    """
    try:
        data = request.files.get("file", None)
        session_id = request.cookies.get("session_id")
        logger.debug(f"File upload requested for session {session_id}")
        
        session = Session.load(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for file upload")
            return jsonify({"status": "failed", "error": "Session not found"})
        
        if not data:
            logger.warning(f"No file provided for upload in session {session_id}")
            return jsonify({"status" : "failed", "error" : "No data found, upload valid file."})
        
        logger.info(f"Uploading file '{data.filename}' for session {session_id}")
        try:
            save_pdf(data, session)
            logger.info(f"File '{data.filename}' saved successfully for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save PDF '{data.filename}': {str(e)}", exc_info=True)
            return jsonify({"status" : "failed", "error" : str(e)})
        
        return jsonify({"status" : "success", "message": f"File '{data.filename}' uploaded successfully"})
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        return jsonify({"status" : "failed", "error" : str(e)})
    
if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("Starting Flask application on 0.0.0.0:5000")
    logger.info("=" * 50)
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}", exc_info=True)
    finally:
        logger.info("Application shutdown")