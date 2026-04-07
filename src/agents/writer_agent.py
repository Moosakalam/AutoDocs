import os 
import json
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
class WriterAgent:
    """
    Agent that generates documentation from analysis.
    Creates README, module docs, onboarding guide.
    """
    
    def __init__(self, retriever, llm_config: dict):
        self.retriever = retriever
        self.llm_config = llm_config
        
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
            name="WriterAgent",
            model_client=model_client,
            system_message="""You are a technical writer specializing in developer documentation.
 
Your documentation should be:
- Clear and concise
- Well-structured with proper markdown formatting
- Include code examples where relevant
- Accessible to developers of varying experience levels
- Focused on practical usage and understanding
 
Generate documentation in markdown format."""
        )
    
    async def generate_documentation(self, analysis_report: dict, 
                                    repo_metadata: dict) -> dict[str, str]:
        """
        Generate complete documentation suite.
        
        Args:
            analysis_report: Output from AnalysisAgent
            repo_metadata: Repository metadata
        
        Returns:
            Dictionary of documentation files (filename -> content)
        """
        print("\n=== WRITER AGENT STARTED ===")
        
        docs = {}
        
        # 1. Generate README
        print("\n[1/3] Generating README.md...")
        readme_context = self.retriever.retrieve_context(
            "Overview of main functionality, key components, usage examples",
            n_results=10
        )
        
        readme_prompt = f"""Generate a comprehensive README.md for this project.
 
Analysis Report:
{json.dumps(analysis_report, indent=2)}
 
Repository Info:
{json.dumps(repo_metadata, indent=2)}
 
Code Context:
{readme_context}
 
Include:
1. Project title and description
2. Architecture overview
3. Key features
4. Installation instructions
5. Quick start guide
6. Core components explanation
7. Usage examples
8. Technology stack
 
Use proper markdown formatting."""
        
        readme_result = await self.agent.run(task=readme_prompt)
        docs['README.md'] = readme_result.messages[-1].content
        
        # 2. Generate Module Documentation
        print("[2/3] Generating MODULE_GUIDE.md...")
        
        # Get unique modules from analysis
        modules = analysis_report.get('core_abstractions', [])
        
        module_guide_prompt = f"""Generate a detailed module guide explaining the codebase structure.
 
Analysis:
{json.dumps(analysis_report, indent=2)}
 
Code Context (retrieve for each major module):
{self.retriever.retrieve_context("Explain main modules and their responsibilities", n_results=15)}
 
Create a guide that explains:
1. Directory structure
2. Each major module's purpose
3. Key classes and their roles
4. Module interdependencies
5. Data flow between modules
 
Format as markdown with clear sections."""
        
        module_result = await self.agent.run(task=module_guide_prompt)
        docs['MODULE_GUIDE.md'] = module_result.messages[-1].content
        
        # 3. Generate Onboarding Guide
        print("[3/3] Generating ONBOARDING.md...")
        
        onboarding_prompt = f"""Generate a developer onboarding guide for new contributors.
 
Analysis:
{json.dumps(analysis_report, indent=2)}
 
Entry Points:
{self.retriever.retrieve_context("Find main entry points and how to run the application", n_results=8)}
 
Create an onboarding guide with:
1. Development environment setup
2. How to run the application
3. How to run tests
4. Recommended first tasks for new contributors
5. Code navigation tips
6. Where to find key functionality
7. Contribution guidelines
 
Make it beginner-friendly but comprehensive."""
        
        onboarding_result = await self.agent.run(task=onboarding_prompt)
        docs['ONBOARDING.md'] = onboarding_result.messages[-1].content
        
        print("\n=== DOCUMENTATION GENERATION COMPLETE ===")
        print(f"Generated {len(docs)} documentation files")
        
        return docs