# Self-RAG Chat Application

A production-grade Retrieval-Augmented Generation (RAG) chatbot application that combines Flask backend with a modern web frontend, using multi-stage LLM reasoning to provide accurate, context-aware responses.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Usage Guide](#usage-guide)
- [Development Notes](#development-notes)

---

## 🎯 Overview

Self-RAG Chat is an advanced AI chat application that implements the Self-Reflective Retrieval-Augmented Generation (Self-RAG) pattern. It enables users to:

- Chat with multiple LLM models (Ollama Cloud)
- Upload and index PDF documents
- Get context-aware responses based on uploaded documents
- Maintain conversation history
- Validate responses against source material

The application uses a microservices architecture with Docker containers for easy deployment and scaling.

---

## ✨ Features

### User Features
- **Multi-Model Support**: Choose between different Ollama Cloud models (Qwen3-vl, GPT-OSS, Mistral-Large-3, Cogito-2.1)
- **PDF Upload & Processing**: Upload PDF documents to create knowledge bases
- **Conversation History**: Maintains session-based conversation history with automatic summarization
- **Session Management**: Isolated user sessions with 30-minute expiration
- **API Key Validation**: Secure API key validation before initialization

### Backend Features
- **Self-RAG Pipeline**: Multi-stage reasoning with:
  - Query rewriting for improved context
  - Automatic retrieval necessity detection
  - Relevance evaluation of retrieved contexts
  - Response generation with context
  - Support verification against source material
  - Utility rating of generated responses
- **Health Monitoring**: Real-time health checks for all microservices
- **Production Logging**: Comprehensive logging with rotation and compression
- **Vector Search**: Semantic search using HuggingFace embeddings and Qdrant

### Infrastructure Features
- **Docker Containerization**: Full Docker Compose deployment
- **Session Storage**: Redis-backed session management
- **Document Storage**: MongoDB with GridFS for large file handling
- **Vector Database**: Qdrant for efficient semantic search
- **Nginx Reverse Proxy**: High-performance web server and load balancing

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Nginx)                         │
│  HTML/CSS/JavaScript - Tailwind CSS UI with Material Icons  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Flask Backend (API)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ API Routes:                                            │ │
│  │ • /health    - Service health checks                  │ │
│  │ • /load      - Session initialization                 │ │
│  │ • /api       - API key validation                     │ │
│  │ • /chat      - Query processing & response generation │ │
│  │ • /new       - Clear conversation history             │ │
│  │ • /upload    - PDF document upload                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Self-RAG Pipeline:                                     │ │
│  │ 1. Rewrite Query  2. Check Retrieval Need             │ │
│  │ 3. Retrieve Docs  4. Check Relevance                  │ │
│  │ 5. Generate Answer 6. Verify Support                  │ │
│  │ 7. Rate Utility                                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────┬─────────────────────────────────────────────────────┘
          │
  ┌───────┼───────────────────┬─────────────────┬──────────────┐
  ▼       ▼                   ▼                 ▼              ▼
[Redis] [MongoDB]        [Qdrant]          [Ollama]      [LangChain]
 Cache   Documents      Vector DB         LLM Models      Orchestration
```

---

## 💻 Technology Stack

### Backend
| Component | Purpose |
|-----------|---------|
| **Flask** | Lightweight web framework for API endpoints |
| **LangChain** | LLM orchestration and RAG pipeline management |
| **Ollama** | Local/Cloud LLM model integration |
| **Qdrant** | Vector database for semantic search |
| **MongoDB** | Document storage with GridFS |
| **Redis** | Session management and caching |
| **Pydantic** | Data validation and serialization |
| **Loguru** | Production-grade logging |
| **sentence-transformers** | Text embedding generation (all-MiniLM-L6-v2) |

### Frontend
| Component | Purpose |
|-----------|---------|
| **HTML5** | Semantic markup |
| **Tailwind CSS** | Utility-first CSS framework |
| **JavaScript (ES6+)** | Interactive features and API communication |
| **Nginx** | Web server and reverse proxy |
| **Material Symbols** | Icon library |

### Infrastructure
| Service | Function |
|---------|----------|
| **Docker/Docker Compose** | Container orchestration |
| **Gunicorn** | WSGI application server |
| **Python 3.11** | Application runtime |

---

## 📝 Prerequisites

Before you begin, ensure you have:

- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
- **Python 3.11+** (for local development)
- **Ollama Account** and API key (https://ollama.com)
- **Git** (for version control)
- Minimum **4GB RAM** for running all containers

---

## 🚀 Installation

### Option 1: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   cd /path/to/project/self-rag
   ```

2. **Build and start containers:**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Backend service on `http://localhost:5000`
   - Frontend service on `http://localhost:8080`
   - Redis cache on `localhost:6379`
   - MongoDB on `localhost:27017`
   - Qdrant vector DB on `localhost:6333`

3. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

### Option 2: Local Development Setup

1. **Create a Python virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Ensure external services are running:**
   ```bash
   # Start Redis
   docker run -d -p 6379:6379 redis:7
   
   # Start MongoDB
   docker run -d -p 27017:27017 mongo:7
   
   # Start Qdrant
   docker run -d -p 6333:6333 qdrant/qdrant:latest
   ```

4. **Start the Flask backend:**
   ```bash
   python app.py
   ```

5. **Start a local web server for frontend:**
   ```bash
   docker run --name webapp --rm -p 8080:80 -v /path/to/frontend:/usr/share/nginx/html:ro -v /path/to/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro --add-host=host.docker.internal:host-gateway nginx:stable

   ```
   The frontend can be accessed at `http://localhost:8080 `

---

## ⚙️ Configuration

### Logging Configuration

Logging is configured in `backend/logging_config.py`:

- **Log Files**: Stored in `backend/logs/`
- **Rotation**: 500MB per file
- **Retention**: 7 days for INFO, 14 days for ERROR
- **Compression**: Automatic ZIP compression of rotated logs
- **Format**: Includes timestamp, level, function, and custom context

View logs:
```bash
# Follow real-time logs
tail -f backend/logs/app.log

# Check error logs
tail -f backend/logs/error.log
```

### Embedding Model

The application uses the lightweight HuggingFace embedding model:
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Distance Metric**: Cosine Similarity
- **Use Case**: Efficient semantic search for RAG

To use a different embedding model, modify in `backend/utils.py`:
```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/model-name"
)
```

---

## 🏃‍♂️ Running the Application

### Start Everything with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

### Health Check

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "ok"}
```

If services are down:
```json
{
  "status": "down",
  "redis": false,
  "mongo": false,
  "qdrant": false
}
```

---

## 🔌 API Endpoints

### Health Check

**GET** `/health`

Check the status of all backend services (Redis, MongoDB, Qdrant).

### Initialize Session

**GET** `/load`

Create a new user session and assign a unique session ID (stored in HTTP-only cookie).

### Reset Conversation

**GET** `/new`

Clear all conversation history for the current session.

### Set API Key

**POST** `/api`

Validate and store the Ollama API key for the session.


### Send Query / Chat

**POST** `/chat`

Process the user's query through the Self-RAG pipeline and return the AI response.


### Upload PDF

**POST** `/upload`

Upload a PDF document to create a knowledge base (requires multipart/form-data).

---

## 📁 Project Structure

```
flask/
├── README.md                          # This file
├── compose.yaml                       # Docker Compose configuration
│
├── backend/
│   ├── app.py                         # Flask application & API endpoints
│   ├── model.py                       # Self-RAG LLM engine & chain definitions
│   ├── utils.py                       # Helper functions (PDF, embedding, storage)
│   ├── session.py                     # Session management (Pydantic models)
│   ├── api_validation.py              # API key validation logic
│   ├── logging_config.py              # Production logging configuration
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Backend container definition
│   ├── logs/                          # Application log files
│      ├── app.log                    # General application logs
│      └── error.log                  # Error logs (preserved longer)
│   
│
├── frontend/
│   ├── index.html                     # Main HTML interface
│   ├── nginx.conf                     # Nginx reverse proxy configuration
│   ├── Dockerfile                     # Frontend container definition
│   └── js/
│       ├── api.js                     # API key management & validation
│       ├── chat.js                    # Chat interface & message handling
│       ├── load.js                    # Session initialization & health checks
        └── logger.js                  # Client-side logging utility


```

## 📱 Usage Guide

### Getting Started

1. **Open the Application**
   - Navigate to http://localhost:8080
   - System automatically creates a session

2. **Set Up Ollama API Key**
   - Get API key from https://ollama.com/account
   - Select desired model from dropdown
   - Paste API key into "OLLAMA API Configuration" section
   - Click "Save Key"
   - Success message: "API Key Saved! Start Chatting!"

3. **Upload Documents (Optional)**
   - Click "Upload File" button
   - Select PDF document
   - System extracts and indexes content
   - Documents are stored in MongoDB GridFS
   - Embeddings are generated with sentence-transformers

4. **Start Chatting**
   - Type your question in the message input
   - System automatically:
     - Checks if document retrieval is needed
     - Searches indexed documents
     - Evaluates result relevance
     - Generates contextual response
     - Verifies response accuracy
   - Conversation history stored for context

5. **Clear History**
   - Click "New Chat"
   - Conversation cleared
   - Session remains active

### Query Examples

**Without Documents:**
- "What is the capital of France?"
- "Explain quantum computing"
- "How does photosynthesis work?"

**With Documents:**
- "What does the document say about X?"
- "Summarize the main points"
- "Find references to Y in the documents"
- "Compare information about Z across documents"

---

### Debugging

**Backend Debugging:**
```bash
# View real-time logs
docker-compose logs -f backend

```

**Frontend Debugging:**
1. Open browser DevTools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab for API failures
4. Check Application/Storage for localStorage values

---

Last Updated: March 2026
