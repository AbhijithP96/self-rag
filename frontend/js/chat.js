// chat.js
// Advanced chat interface with production-level logging and error handling
import { Logger } from "./logger.js";

const logger = new Logger('CHAT');

const MAX_MESSAGE_LENGTH = 5000;
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ALLOWED_FILE_TYPES = ['.pdf'];
const API_TIMEOUT = 60000 * 30; // 30 minutes

// Get references to DOM elements
const chat_head = document.getElementById("startup-head");
const playground = document.getElementById("playground");
const sndbtn = document.getElementById("sndbtn");
const query = document.getElementById("query");
const newbtn = document.getElementById("new");
const uploadbtn = document.getElementById("upload");

// Validate DOM elements
if (!chat_head || !playground || !sndbtn || !query || !newbtn || !uploadbtn) {
    logger.error('Missing required DOM elements');
    window.alert('Page initialization error. Please refresh.');
}

// Function to start a new chat session
function newChat() {
    try {
        playground.innerHTML = ''; 
        if (chat_head.classList.contains("hidden")) { 
            chat_head.classList.remove("hidden");
        }
        logger.info('New chat session started');
    } catch (error) {
        logger.error('Error creating new chat', { message: error.message });
        window.alert('Error creating new chat. Please try again.');
    }
}

// Function to add a message to the chat interface
function addmessage(text, sender) {
    try {
        if (!text || typeof text !== 'string') {
            logger.warn('Invalid message text', { sender, text });
            return false;
        }

        if (sender !== 'user' && sender !== 'ai') {
            logger.warn('Invalid sender type', { sender });
            return false;
        }

        // Wrapper div for alignment (full width, flexbox for alignment)
        const wrapper = document.createElement("div");
        wrapper.classList.add("w-full", "flex");
        
        // Align user messages to the left and AI messages to the right
        if (sender === "user") {
            wrapper.classList.add("justify-start");
        } else {
            wrapper.classList.add("justify-end");
        }

        // Message container with styling
        const msg = document.createElement("div");
        msg.classList.add("message", sender, "flex", "gap-1", "max-w-xs", "md:max-w-md", "flex-wrap");
        
        // Add an icon to differentiate between user and AI messages
        const icon = document.createElement("span");
        icon.classList.add("icon", "flex-shrink-0");
        icon.textContent = sender === "user" ? '👤' : '🤖';

        // Text content of the message
        const newtext = document.createElement("span");
        newtext.classList.add("text", "break-words");
        newtext.textContent = text;

        msg.appendChild(icon);
        msg.appendChild(newtext);
        
        wrapper.appendChild(msg);
        playground.appendChild(wrapper);
        
        // Auto-scroll to bottom
        playground.scrollTop = playground.scrollHeight;

        // Add a line break after each message
        const linebreak = document.createElement("br"); 
        playground.appendChild(linebreak);

        logger.debug('Message added to chat', { sender, textLength: text.length });
        return true;
    } catch (error) {
        logger.error('Error adding message', { message: error.message, sender });
        return false;
    }
}

// Function to call the AI API and get a response with timeout and error handling
async function call_ai(text, session_id) {
    if (!text || !session_id) {
        logger.error('Invalid parameters for call_ai', { hasText: !!text, hasSession: !!session_id });
        throw new Error('Invalid parameters');
    }

    try {
        logger.info('Calling AI API', { textLength: text.length, session_id: session_id.substring(0, 8) });
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

        const response = await fetch("/chat", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ 
                query: text,
                session_id: session_id
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            logger.error('AI API error response', { status: response.status });
            throw new Error(`API returned status ${response.status}`);
        }

        const data = await response.json();
        logger.debug('AI response received', { status: data.status });

        if (data.status === "success") {
            if (!data.response) {
                logger.error('Empty response from AI');
                throw new Error('Empty response from AI');
            }
            
            const added = addmessage(data.response, 'ai');
            if (!added) {
                logger.error('Failed to add AI message to chat');
                throw new Error('Failed to display message');
            }
            logger.info('AI response displayed successfully');
        } else {
            logger.error('AI API request failed', { 
                status: data.status, 
                message: data.message 
            });
            throw new Error(data.message || 'AI request failed');
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            logger.error('AI API request timeout', { timeout: API_TIMEOUT });
            window.alert("API Time Limit Reached!")
            throw new Error('Request timeout - the AI took too long to respond');
        }
        if (error instanceof TypeError) {
            logger.error('Network error calling AI', { message: error.message });
            throw new Error('Network error - please check your connection');
        }
        logger.error('Unexpected error calling AI', { 
            message: error.message,
            type: error.name
        });
        throw error;
    }
}

// Event listener for the upload button to handle file uploads
uploadbtn.addEventListener("click", () => {
    try {
        logger.info('Upload button clicked');
        
        // Create a hidden file input element to trigger the file selection dialog
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = ALLOWED_FILE_TYPES.join(',');
        
        // Handle the file selection and upload process
        fileInput.onchange = async () => {
            const file = fileInput.files[0];
            
            if (!file) {
                logger.info('File selection cancelled');
                return;
            }

            try {
                // Validate file
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                if (!ALLOWED_FILE_TYPES.includes(fileExt)) {
                    logger.warn('Invalid file type selected', { fileExt, fileName: file.name });
                    window.alert(`Invalid file type. Allowed types: ${ALLOWED_FILE_TYPES.join(', ')}`);
                    return;
                }

                if (file.size > MAX_FILE_SIZE) {
                    logger.warn('File too large', { fileSize: file.size, maxSize: MAX_FILE_SIZE });
                    window.alert(`File too large. Maximum size: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
                    return;
                }

                logger.info('File validation passed', { fileName: file.name, fileSize: file.size });
                
                const session_id = localStorage.getItem("session_id");
                if (!session_id) {
                    logger.error('Session ID not available for file upload');
                    window.alert("Session error. Please refresh and try again.");
                    return;
                }

                const formData = new FormData();
                formData.append("file", file);
                formData.append("session_id", session_id);

                logger.info('Starting file upload', { fileName: file.name });

                const response = await fetch("/upload", {
                    method: "POST",
                    credentials: "include",
                    body: formData,
                    timeout: 60000 // 60 seconds for file upload
                });

                const data = await response.json();

                if (response.ok && data.status === "success") {
                    logger.info('File uploaded successfully', { fileName: file.name });
                    window.alert("File uploaded successfully.");
                    addmessage(`Uploaded: ${file.name}`, 'user');
                } else {
                    logger.error('File upload failed', { 
                        status: response.status,
                        error: data.error || data.message
                    });
                    window.alert(`File upload failed: ${data.error || data.message || 'Unknown error'}`);
                }
            } catch (error) {
                logger.error('File upload error', { 
                    message: error.message,
                    type: error.name
                });
                window.alert("An error occurred while uploading the file. Please try again.");
            }
        };
        
        fileInput.click();
    } catch (error) {
        logger.error('Error in upload button handler', { message: error.message });
        window.alert('An error occurred. Please try again.');
    }
});

// Event listener for the send button to handle sending messages
sndbtn.addEventListener("click", async () => {
    try {
        logger.info('Send button clicked');
        
        // Check API status first
        if (localStorage.getItem("API_STATUS") !== "1") {
            logger.warn('Attempted to send message without valid API key');
            window.alert("No valid API key set. Please configure API settings first.");
            return;
        }

        const text = query.value.trim();

        // Validate message
        if (!text) {
            logger.debug('Empty message prevented');
            return;
        }

        if (text.length > MAX_MESSAGE_LENGTH) {
            logger.warn('Message exceeds max length', { length: text.length, max: MAX_MESSAGE_LENGTH });
            window.alert(`Message too long. Maximum: ${MAX_MESSAGE_LENGTH} characters`);
            return;
        }

        // Hide startup message if visible
        if (!chat_head.classList.contains("hidden")) {
            chat_head.classList.add("hidden");
        }

        // Add user message and clear input
        addmessage(text, 'user');
        query.value = '';

        const session_id = localStorage.getItem("session_id");
        if (!session_id) {
            logger.error('Session ID not found for message sending');
            addmessage("Error: Session not initialized. Please refresh the page.", 'ai');
            return;
        }

        logger.debug('Sending message to AI', { 
            messageLength: text.length,
            sessionId: session_id.substring(0, 8)
        });

        try {
            await call_ai(text, session_id);
        } catch (error) {
            logger.error('AI call failed', { message: error.message });
            addmessage(`Sorry, something went wrong: ${error.message}. Please try again.`, 'ai');
        }
    } catch (error) {
        logger.error('Unexpected error in send handler', { message: error.message });
        addmessage("An unexpected error occurred. Please try again later.", 'ai');
    }
});

// Allow pressing Enter to send the message
query.addEventListener('keypress', (e) => {
    try {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            logger.debug('Enter key pressed for message send');
            sndbtn.click();
        }
    } catch (error) {
        logger.error('Error in keypress handler', { message: error.message });
    }
});

// Event listener for the new chat button to start a new chat session
newbtn.addEventListener("click", () => {
    try {
        logger.info('New chat button clicked');
        newChat();
    } catch (error) {
        logger.error('Error in new chat button handler', { message: error.message });
        window.alert('Error starting new chat. Please try again.');
    }
});


