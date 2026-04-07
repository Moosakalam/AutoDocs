# 🤖 AutoDoc: Autonomous Multi-Agent Documentation System

AutoDoc is an autonomous, multi-agent artificial intelligence system designed to revolutionize how engineering teams handle software documentation. By acting as a virtual senior engineering team, AutoDoc transforms the time-consuming task of writing documentation from a multi-day chore into a seamless, five-minute automated process.

Powered by **AutoGen**, **ChromaDB**, and **Tree-sitter**, it uses Abstract Syntax Tree (AST) parsing and Retrieval-Augmented Generation (RAG) to semantically map architecture, write guides, and detect its own hallucinations.

---

## ✨ Key Features

* **Multi-Agent Architecture:** Utilizes 5 specialized AI agents (Ingestion, Analysis, Writer, QA, Reviewer) orchestrated via AutoGen 0.4.
* **AST-Based Chunking:** Instead of splitting text by arbitrary character limits, AutoDoc uses `tree-sitter` to chunk code intelligently by semantic boundaries (functions and classes).
* **Automated Hallucination Detection:** A dedicated QA agent cross-references all generated claims against the vector database to ensure absolute factual accuracy.
* **Interactive Dashboard:** Includes a sleek, local Streamlit web UI to run the pipeline, view metrics (Quality Score, Code Chunks Analyzed), and browse generated markdown files.
* **Universal Compatibility:** Can document local project paths or clone and document public GitHub repositories on the fly.

---

## 🏗️ The 5-Agent Pipeline

1. **Ingestion Agent 🔍:** Clones the repo, parses it using Tree-sitter, and creates a semantic vector database in ChromaDB.
2. **Analysis Agent 📐:** Queries the vector store to map dependencies, identify core design patterns (e.g., Factory, Adapter), and find entry points.
3. **Writer Agent ✍️:** Takes the architectural blueprint and drafts the actual markdown files (`README.md`, `MODULE_GUIDE.md`, `ONBOARDING.md`).
4. **QA Agent 🚨:** *The Hallucination Detector.* Extracts factual claims from the generated docs and strictly cross-references them against original code snippets.
5. **Reviewer Agent ⭐:** Scores the final output on Completeness, Clarity, and Accuracy, delivering a final JSON diagnostic report.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* [Docker](https://www.docker.com/) (Optional, for containerized deployment)
* API Keys for your preferred LLM (OpenAI, Google Gemini, or Groq)

### 2. Installation
Clone the repository and install the required dependencies:

```bash
git clone [https://github.com/yourusername/AutoDocs.git](https://github.com/yourusername/AutoDocs.git)
cd AutoDocs

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
