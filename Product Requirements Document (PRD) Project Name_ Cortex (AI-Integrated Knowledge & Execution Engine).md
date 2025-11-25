# **Product Requirements Document (PRD)**

Project Name: Cortex (AI-Integrated Knowledge & Execution Engine)  
Version: 1.0  
Target Hardware: AMD Ryzen AI MAX+ 395 / Radeon 8060S (128GB Shared Memory)

## **1\. Executive Summary**

Cortex is a local, single-user intelligence platform designed to ingest massive amounts of unstructured personal data (chat history, research reports, code repositories) and structure them into actionable project roadmaps. Unlike standard RAG (Retrieval-Augmented Generation) systems that simply answer questions, Cortex focuses on **Project Execution**: turning "Idea Debt" into finished software/products by visualizing decision trees, utilizing local AI agents, and automating workflows.

## **2\. Problem Statement**

The user possesses a vast repository of intellectual property (1000+ reports, 50+ repos, 10+ chat histories) but lacks a cohesive system to synthesize this information. Current tools (like NotebookLM) provide organization but lack total data visibility and fail to provide actionable, step-by-step project management flows derived from that data.

## **3\. Goals & Objectives**

* **Total Ingestion:** Unify disparate data sources (JSON, Markdown, PDF, Code) into a single queryable vector space.  
* **Project Intelligence:** Automatically extract "unfinished projects" and "ideas" from chat logs.  
* **Visual Decision Making:** Move beyond chat interfaces to a "Roadmap" interface where project paths are visualized as diagrams with decision nodes.  
* **Local Sovereignty:** Run entirely on local AMD hardware using optimized ROCm libraries.

## **4\. Technical Constraints & Stack**

* **Hardware:** AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (128GB APU).  
* **Backend Environment:**  
  * **OS/Drivers:** ROCm 7.1.0 (Optimized).  
  * **Language:** Python 3.11.  
  * **ML Libraries:** PyTorch 2.9, TorchVision, TorchAudio, Triton.  
  * **Inference:** vLLM / llama.cpp.  
* **Orchestration:** LangGraph (Stateful Agents), LangChain (Chains), n8n (Workflow Automation).  
* **Frontend:** React (Cyberpunk Theme).

## **5\. Key Features**

### **5.1 The Data Ingestion Pipeline**

* **Multi-Format Support:** Ingest PDFs, Markdown, JSON, Codebases, and Screenshots.  
* **Chat History Parser:** specifically trained parser to read exports from other AI services to distinguish between "chit-chat" and "project ideas/code."  
* **Contextual Linking:** Automatically link a PDF research report to a Code Repository if the topics match.

### **5.2 The Dynamic Project Roadmap (The Core Feature)**

* **Diagrammatic View:** Instead of a task list, projects are displayed as a Flowchart/DAG (Directed Acyclic Graph).  
* **Decision Nodes:** Points in the roadmap where variables exist (e.g., "Choose Database").  
* **Deep Dive Context:** Clicking a node provides data from the local knowledge base to help make the decision (e.g., "Here is your previous research on Vector DBs").  
* **Agentic Branching:** If a path is chosen, LangGraph agents spin up to generate the next steps for that specific branch.

### **5.3 Real-Time Agent Visualization**

* **Under-the-Hood View:** A dedicated UI overlay that visualizes the LangGraph state machine in real-time.  
* **Activity Logs:** See exactly which document the AI is reading or which tool (n8n workflow) it is triggering.

### **5.4 Code & Repository Analysis**

* **Repo Ingestion:** Index local git repositories.  
* **Gap Analysis:** Compare current code (Repo) against desired features (Chat History) to suggest code updates.

## **6\. User Experience (UX)**

* **Theme:** "Darkish Cyberpunk" – High contrast, neon accents (purple/teal), data-dense dashboards, glass-morphism panels.  
* **Navigation:** Spatial navigation (Zoomable UI) rather than paginated lists.  
* **Interaction:** Hybrid Chat \+ Graphical User Interface (GUI). You talk to the map, and the map updates.

## **7\. Success Metrics**

* Reduction in time to locate specific code snippets or ideas from history.  
* Successful conversion of an "old chat idea" into a "structured project roadmap."  
* Smooth performance (tokens per second) on the 128GB APU without OOM errors.