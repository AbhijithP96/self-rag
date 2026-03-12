from ollama import Client
from logging_config import logger

def validate_api(api_key):
    """Validate API key by making a test request.
    
    Args:
        api_key: API key to validate
        
    Returns:
        tuple: (response_message, is_valid) where is_valid is boolean
    """
    try:
        logger.debug("Validating API key")
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': 'Bearer ' + api_key})

        messages = [{
            'role' : 'system',
            'content' : 'You are a helpful assistant that answers questions from user.'  
        },
        {
            'role': 'user',
            'content': 'Why is the sky blue?',
        },]

        try:
            response = client.chat('gpt-oss:120b', messages=messages)
            logger.info("API key validation successful")
            return response.message.content, True
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"API key validation failed: {error_msg}")
            return error_msg, False
    except Exception as e:
        logger.error(f"Unexpected error during API validation: {str(e)}", exc_info=True)
        return str(e), False

