// Production Logger Utility (shared across modules)
import { Logger } from "./logger.js";

const logger = new Logger('LOAD');
const MAX_HEALTH_RETRIES = 3;
const HEALTH_RETRY_DELAY = 1000; // 1 second

async function healthcheck(retryCount = 0) {
    try {
        logger.info(`Health check attempt ${retryCount + 1}/${MAX_HEALTH_RETRIES}`);
        
        const response = await fetch("/health", { 
            method: "GET",
            timeout: 5000
        });

        if (!response.ok) {
            throw new Error(`Health check returned status ${response.status}`);
        }

        const data = await response.json();
        logger.debug('Health check response received', { status: data.status });

        if (data.status === "ok") {
            logger.info("Health check passed");
            return true; // indicate success
        } else {
            logger.warn("Health check failed: services might be down", data);
            
            // Retry logic for transient failures
            if (retryCount < MAX_HEALTH_RETRIES - 1) {
                logger.info(`Retrying health check after ${HEALTH_RETRY_DELAY}ms`);
                await new Promise(resolve => setTimeout(resolve, HEALTH_RETRY_DELAY));
                return healthcheck(retryCount + 1);
            }
            
            window.alert("Backend services are unavailable. Please try again later.");
            return false;
        }
    } catch (error) {
        logger.error("Health check error", { 
            message: error.message, 
            type: error.name,
            attempt: retryCount + 1
        });

        // Retry on network errors
        if (error instanceof TypeError && retryCount < MAX_HEALTH_RETRIES - 1) {
            logger.info(`Retrying health check after network error`);
            await new Promise(resolve => setTimeout(resolve, HEALTH_RETRY_DELAY));
            return healthcheck(retryCount + 1);
        }

        window.alert("Unable to connect to server. Please check your connection.");
        return false; // indicate failure
    }
}

async function on_load() {
    try {
        logger.info('Creating new session');
        
        const response = await fetch('/load', { 
            method: "GET",
            credentials: "include",
            timeout: 10000
        });

        if (!response.ok) {
            throw new Error(`Session creation failed with status ${response.status}`);
        }

        const data = await response.json();

        if (data.status === "success") {
            logger.info("New session created", { session_id: data.session_id });
            localStorage.setItem("session_id", data.session_id);
            return true;
        } else {
            logger.error("Session creation failed", { 
                message: data.message, 
                status: data.status 
            });
            window.alert("Failed to create session. " + (data.message || 'Please try again.'));
            return false;
        }
    } catch (error) {
        logger.error("Session creation error", { 
            message: error.message, 
            type: error.name 
        });
        window.alert("Error creating session. Please refresh the page.");
        return false;
    }
}

// on page load
window.addEventListener("DOMContentLoaded", async () => {
    try {
        logger.info("Page load detected, initializing");

        const healthy = await healthcheck();

        if (healthy) {
            const sessionCreated = await on_load(); // only create session if healthcheck passes
            
            if (sessionCreated) {
                logger.info("Initialization completed successfully");
            } else {
                logger.warn("Session creation failed during initialization");
            }
        } else {
            logger.warn("Health check failed, serving static page only");
        }
    } catch (error) {
        logger.error("Unexpected error during initialization", { 
            message: error.message,
            type: error.name
        });
        window.alert("Initialization error. Please refresh the page.");
    }
});