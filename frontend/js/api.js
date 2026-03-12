// Production Logger Utility
import { Logger } from "./logger.js";
const logger = new Logger('API');

// Get references to DOM elements
const apiKey = document.getElementById("api");
const savebtn = document.getElementById("save");
const togglebtn = document.getElementById("toggle-visibility");
const modelSelect = document.getElementById("model-select");

let model_name = modelSelect.value;
logger.info('Selected Model is: ' + model_name);
// Check if API key status is stored in localStorage, if not set it to "0" (not set)
if (!localStorage.getItem("API_STATUS")) {
    localStorage.setItem("API_STATUS", "0");
    logger.info('Initialized API status to 0');
}

// Function to get the API key from the input field and validate it with the backend
async function get_api_key() {
    const api = apiKey.value.trim();

    // Validate input
    if (api === '') {
        logger.warn('API key validation failed: empty input');
        window.alert("No key entered");
        return;
    }

    logger.info('Attempting to validate API key');
    
    try {
        const session_id = localStorage.getItem("session_id");
        
        if (!session_id) {
            logger.error('Session ID not found in localStorage');
            window.alert("Session error. Please refresh the page.");
            return;
        }

        const response = await fetch("/api", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                api_key: api,
                model: model_name,
                session_id: session_id
            }),
            timeout: 10000 // 10 second timeout
        });

        // Handle HTTP errors
        if (!response.ok) {
            logger.error('API validation request failed', { status: response.status });
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        logger.info('API validation response received', { status: data.status });

        if (data.status === "failed") {
            logger.warn('API key validation failed', { reason: data.error || 'unknown' });
            window.alert("Wrong API Provided. Please Check Readme to set up OLLAMA API key.");
            localStorage.setItem("API_STATUS", "0");
        } else if (data.status === "success") {
            logger.info('API key validated successfully');
            window.alert("API Key Saved! Start Chatting!");
            localStorage.setItem("API_STATUS", "1");
        } else {
            logger.error('Unexpected API response status', { status: data.status });
            window.alert("Unexpected server response. Please try again.");
            localStorage.setItem("API_STATUS", "0");
        }

        apiKey.value = ''; // Clear input after processing

    } catch (error) {
        logger.error('API key validation error', { 
            message: error.message, 
            type: error.name 
        });
        
        if (error instanceof TypeError) {
            window.alert("Network error. Please check your connection.");
        } else {
            window.alert("An error occurred. Please try again later.");
        }
        
        localStorage.setItem("API_STATUS", "0");
    }
}

// Event listener for the save button to trigger API key validation and saving
savebtn.addEventListener('click', () => {
    logger.info('Save button clicked');
    logger.info('Model using for this session:', model_name)
    modelSelect.disabled = true;
    get_api_key();
});

// Event listener for the toggle visibility button to show/hide the API key
togglebtn.addEventListener("click", () => {
    try {
        if (apiKey.type === "password") {
            apiKey.type = "text";
            togglebtn.textContent = "visibility";
            logger.info('API key visibility toggled: shown');
        } else {
            apiKey.type = "password";
            togglebtn.textContent = "visibility_off";
            logger.info('API key visibility toggled: hidden');
        }
    } catch (error) {
        logger.error('Error toggling visibility', { message: error.message });
    }
});

modelSelect.addEventListener("change", () => {
    model_name = modelSelect.value;
    logger.info('Selected Model is: '+ model_name);
})