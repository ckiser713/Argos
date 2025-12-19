# **System Blueprint & Architecture: Project Cortex**

## **1\. High-Level Architecture Diagram**

graph TD  
    User\[User (React Frontend)\] \<--\> API\[FastAPI Middleware\]  
    API \<--\> Orchestrator\[LangGraph / LangChain\]  
      
    subgraph "Local Hardware (AMD Ryzen AI MAX+)"  
        Orchestrator \<--\> Inference\[vLLM / llama.cpp (ROCm 7.1)\]  
        Orchestrator \<--\> Workflow\[n8n Automation Engine\]  
        Orchestrator \<--\> VectorDB\[Vector Database (Chroma/Qdrant)\]  
          
        VectorDB \<--\> Ingestion\[Ingestion Pipeline\]  
    end  
      
    subgraph "Data Sources"  
        ChatLogs\[Chat Histories\]  
        Repos\[Git Repositories\]  
        Docs\[PDFs/Research\]  
    end  
      
    Ingestion \--\> ChatLogs  
    Ingestion \--\> Repos  
    Ingestion \--\> Docs

## **2\. Component Details**

### **A. The Frontend (React \+ Cyberpunk UI)**

* **Framework:** React 18+ (Vite).  
* **State Management:** Zustand (for handling complex roadmap states).  
* **Visualization Library:** React Flow or Cytoscape.js (for the Project Roadmap and LangGraph visualization).  
* **Theme Engine:** Tailwind CSS with custom Cyberpunk config (Neon glows, dark backgrounds, monospace fonts).  
* **Key Views:**  
  1. **The Command Center:** A dashboard showing active agents, system stats (VRAM usage), and recent insights.  
  2. **The Canvas:** An infinite canvas where Project Roadmaps are drawn.  
  3. **The Neural Link:** A search interface that queries the vector DB and displays results as interconnected nodes.

### **B. The Orchestration Layer (LangGraph \+ n8n)**

* **LangGraph:** Handles the state of the "Project Manager" agent. It remembers where you are in the roadmap.  
  * *Node:* Supervisor Agent (Routes tasks).  
  * *Node:* Coder Agent (Retrieves/Generates code).  
  * *Node:* Researcher Agent (Queries PDF library).  
* **n8n (Local Host):** Used for deterministic workflows.  
  * *Example:* "When a project status changes to 'Building', trigger a git commit in the local repo."  
  * *Example:* "Daily scrape of specific tech news to update the Research DB."

### **C. The Inference Engine (The Brain)**

* **Hardware Optimization:** \* Specific compilation of vLLM for ROCm 7.1 to utilize the 128GB unified memory.  
  * Context Window optimization: Utilizing the large RAM to allow for 128k+ context windows (essential for reading entire codebases).  
* **Model Strategy:**  
  * *Primary Brain:* Llama-3 (70B or similar high-param model) for complex logic and roadmap generation.  
  * *Coding Specialist:* DeepSeek-Coder or CodeLlama (quantized) for repo analysis.

### **D. The Data Layer (RAG)**

* **Vector Store:** Qdrant (Docker container). It supports hybrid search (Keyword \+ Vector) which is crucial for finding specific variable names in code.  
* **Embeddings:** BGE-M3 (or similar high-performance embedding model running locally).  
* **Graph Database (Optional):** Neo4j (if relationship complexity between "Ideas" and "Files" becomes too dense for just vector search).

## **3\. The "Dynamic Roadmap" Logic Flow**

This is the unique selling point logic:

1. **User Input:** "I want to build that trading bot we talked about 3 months ago."  
2. **Retrieval:** System searches VectorDB for "trading bot" \+ "3 months ago" context.  
3. **Synthesis:** LLM summarizes the idea, the required tech stack defined in the past, and current research papers.  
4. **Generation:** LangGraph generates a JSON structure representing a DAG (Directed Acyclic Graph).  
   * *Phase 1:* Setup Env.  
   * *Phase 2:* Data Pipeline.  
   * *Decision Node A:* "Choose API (Polygon vs AlphaVantage)?"  
5. **Visualization:** Frontend renders this JSON as an interactive React Flow diagram.  
6. **Interaction:** User clicks "Decision Node A".  
7. **Contextual Help:** A sidebar opens showing cost analysis of Polygon vs AlphaVantage based on cached PDF reports.

## **4\. Implementation Phases**

* **Phase 1: Foundation.** Setup AMD ROCm environment, verify vLLM performance, build basic Ingestion Pipeline for Chat Logs.  
* **Phase 2: The Brain.** Implement LangGraph agent capable of simple RAG.  
* **Phase 3: The UI.** Build the Cyberpunk React frontend and connect it to the API.  
* **Phase 4: Visual Intelligence.** Implement the React Flow roadmap and real-time agent visualization.  
* **Phase 5: Automation.** Integrate n8n for background tasks.