from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from typing import Dict, List
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os 
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
class AnalysisAgent:
    """
    Agent that analyzes codebase structure using RAG.
    Queries vector store to understand dependencies, patterns, architecture.
    """
    
    def __init__(self, retriever, llm_config: Dict):
        """
        Initialize analysis agent with RAG retriever and LLM.
        
        Args:
            retriever: CodeRetriever instance
            llm_config: LLM configuration dict
        """
        self.retriever = retriever
        self.llm_config = llm_config
        
        # Create AutoGen assistant with OpenAI
        model_client =OpenAIChatCompletionClient(
    model="openai/gpt-oss-120b",  # Use the specific NVIDIA model name
    base_url = "https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("Nvidia-NIM"),
    
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown"
    }
)
        
        self.agent = AssistantAgent(
            name="AnalysisAgent",
            model_client=model_client,
            system_message="""You are a senior software architect analyzing codebases.
            
Your task is to:
1. Identify the overall architecture and design patterns
2. Map dependencies between modules
3. Find entry points (main files, API endpoints)
4. Detect code organization patterns
5. Identify core abstractions and their relationships
 
Return your analysis as structured JSON with these sections:
- architecture_type: (e.g., "microservices", "monolith", "layered")
- design_patterns: list of patterns used
- entry_points: list of main files/functions
- module_dependencies: dependency map
- core_abstractions: key classes/interfaces
- technology_stack: frameworks and libraries used
"""
        )
    
    async def analyze_codebase(self, repo_metadata: Dict) -> Dict:
        """
        Main analysis workflow using RAG queries.
        
        Args:
            repo_metadata: Repository metadata from ingestion
        
        Returns:
            Structured analysis report as JSON
        """
        print("\n=== ANALYSIS AGENT STARTED ===")
        
        # Query 1: Identify entry points
        print("\n[1/5] Identifying entry points...")
        entry_context = self.retriever.retrieve_context(
            "Find main entry points: main functions, app initialization, API routes, CLI entry points",
            n_results=10
        )
        
        # Query 2: Find architectural patterns
        print("[2/5] Analyzing architecture patterns...")
        arch_context = self.retriever.retrieve_context(
            "Identify architectural patterns: MVC, microservices, layered architecture, design patterns",
            n_results=10
        )
        
        # Query 3: Map dependencies
        print("[3/5] Mapping module dependencies...")
        dep_context = self.retriever.retrieve_context(
            "Find import statements, dependencies between modules, external libraries used",
            n_results=15
        )
        
        # Query 4: Core abstractions
        print("[4/5] Identifying core abstractions...")
        core_context = self.retriever.retrieve_context(
            "Find main classes, interfaces, base classes, core data structures",
            n_results=10
        )
        
        # Query 5: Technology stack
        print("[5/5] Detecting technology stack...")
        tech_context = self.retriever.retrieve_context(
            "Identify frameworks, libraries, databases, external services used",
            n_results=10
        )
        
        # Combine all context
        full_context = f"""
Repository Analysis Context:
 
{repo_metadata}
 
=== Entry Points ===
{entry_context}
 
=== Architecture Patterns ===
{arch_context}
 
=== Dependencies ===
{dep_context}
 
=== Core Abstractions ===
{core_context}
 
=== Technology Stack ===
{tech_context}
"""
        
        # Run analysis with LLM
        print("\n[LLM] Processing analysis...")
        from autogen_agentchat.messages import TextMessage
        from autogen_agentchat.base import TaskResult
        
        result = await self.agent.run(
            task=f"""Analyze the codebase based on the provided context.
            
{full_context}
 
Return ONLY a valid JSON object with the analysis structure defined in your system message.
No markdown, no code blocks, just pure JSON."""
        )
        
        # Extract and parse JSON from response
        response_text = result.messages[-1].content
        
        # Clean response (remove markdown if present)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        try:
            analysis_report = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Raw response: {response_text[:500]}")
            # Fallback: return raw text
            analysis_report = {"raw_analysis": response_text, "error": str(e)}
        
        print("\n=== ANALYSIS COMPLETE ===")
        return analysis_report
 
 