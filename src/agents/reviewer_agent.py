import json
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
class ReviewerAgent:
    """
    Agent that scores documentation quality and coverage.
    Provides final quality metrics.
    """
    
    def __init__(self, retriever, vector_store, llm_config: dict):
        self.retriever = retriever
        self.vector_store = vector_store
        self.llm_config = llm_config
        
        model_client =OpenAIChatCompletionClient(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("OPENAI_API_KEY"), # Or however you're passing keys
        base_url="https://api.groq.com/openai/v1", # Ensure this is set for Groq
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="unknown" # Or "llama3"
        )
    )
        
        self.agent = AssistantAgent(
            name="ReviewerAgent",
            model_client=model_client,
            system_message="""You are a documentation quality reviewer.
 
Evaluate documentation on:
1. Completeness (all components documented)
2. Clarity (easy to understand)
3. Accuracy (verified against code)
4. Structure (well-organized)
5. Usefulness (actionable for developers)
 
Provide scores 0-10 for each dimension and overall quality score."""
        )
    
    async def review_documentation(self, docs: dict[str, str], 
                                  validation_report: dict,
                                  analysis_report: dict) -> dict:
        print("\n=== REVIEWER AGENT STARTED ===")
        
        # Calculate coverage metrics
        print("\n[1/2] Calculating coverage metrics...")
        coverage = self._calculate_coverage(docs, analysis_report)
        
        # Generate quality assessment
        print("[2/2] Assessing documentation quality...")
        
        # FIX: Using .get() with defaults to prevent KeyErrors
        claims_checked = validation_report.get('count', 0)
        issues_found = validation_report.get('issues_found', len(validation_report.get('issues', [])))
        critical_issues = validation_report.get('critical_issues', 0)

        review_prompt = f"""Review the generated documentation quality.
 
Documentation Files:
{list(docs.keys())}
 
Validation Report:
- Claims checked: {claims_checked}
- Issues found: {issues_found}
- Critical issues: {critical_issues}
 
Coverage Metrics:
{json.dumps(coverage, indent=2)}
 
Sample from README:
{docs.get('README.md', '')[:1000]}...
 
Return JSON with scores (0-10), strengths, weaknesses, and recommendations.
"""
        
        # Add retry logic similar to QAAgent if you hit rate limits here too
        result = await self.agent.run(task=review_prompt)
        response = result.messages[-1].content
        
        # Parse review
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            quality_review = json.loads(response.strip())
        except json.JSONDecodeError:
            quality_review = {"error": "Failed to parse review", "raw": response}
        
        # FIX: Final summary using safe key access
        final_review = {
            **quality_review,
            'coverage': coverage,
            'validation_summary': {
                'total_checks': claims_checked,
                'issues': issues_found,
                'critical': critical_issues
            }
        }
        
        print("\n=== REVIEW COMPLETE ===")
        print(f"Overall Quality Score: {quality_review.get('scores', {}).get('overall', 'N/A')}/10")
        
        return final_review
    
    def _calculate_coverage(self, docs: dict, analysis_report: dict) -> dict:
        """Calculate what percentage of codebase is documented."""
        
        # Get total chunks in vector store
        stats = self.vector_store.get_collection_stats()
        total_chunks = stats['total_documents']
        
        # Estimate documented components (simplified)
        # In production: search for each component in docs
        documented_components = len(analysis_report.get('core_abstractions', []))
        total_components = documented_components + 5  # Rough estimate
        
        return {
            'total_code_chunks': total_chunks,
            'documented_components': documented_components,
            'total_components_estimate': total_components,
            'coverage_percentage': (documented_components / total_components * 100) if total_components > 0 else 0,
            'files_generated': len(docs)
        }