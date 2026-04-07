import os 
import json
import asyncio
from typing import Dict, List
from openai import RateLimitError
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from autogen_agentchat.agents import AssistantAgent

class QAAgent:
    def __init__(self, retriever, llm_config: dict):
        self.retriever = retriever
        
        # Use llama-3.1-8b-instant if you keep hitting limits; 
        # it's 10x more lenient with TPM than the 70b model.
        model_client = OpenAIChatCompletionClient(
            model="llama-3.1-8b-instant", 
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            model_info=ModelInfo(vision=False, function_calling=True, json_output=True, family="unknown")
        )
        
        # MINIMIZED: System message is now just a core directive.
        self.agent = AssistantAgent(
            name="QA",
            model_client=model_client,
            system_message="Verify docs vs code. Reply ONLY with JSON."
        )

    async def _run_with_retry(self, prompt: str):
        """Exponential backoff to handle the 429s."""
        for attempt in range(3):
            try:
                result = await self.agent.run(task=prompt)
                return result.messages[-1].content
            except RateLimitError:
                wait = (attempt + 1) * 3
                print(f"  ⏳ Limit hit, waiting {wait}s...")
                await asyncio.sleep(wait)
        return None

    async def validate_documentation(self, docs: Dict[str, str], analysis_report: Dict) -> Dict:
        print("\n=== QA AGENT (Token-Optimized) ===")
        validation_issues = []
        
        for doc_name, doc_content in docs.items():
            # Only check the most important claims to save tokens
            claims = self._extract_claims(doc_content)[:3] 
            
            for claim in claims:
                # TOKEN SAVER: n_results=2. Usually enough to find the relevant function.
                evidence = self.retriever.retrieve_context(claim, n_results=2)
                
                # MINIMIZED: Very short prompt, no fluff.
                prompt = f"Claim:{claim}\nCode:{evidence}\nReturn JSON:{{status:verified|hallucination|inconsistent, severity:minor|major, fix:str}}"
                
                raw_response = await self._run_with_retry(prompt)
                if not raw_response: continue

                try:
                    # Clean the response for the JSON parser
                    clean_json = raw_response.strip().replace("```json", "").replace("```", "")
                    res = json.loads(clean_json)
                    
                    if res.get('status') != 'verified':
                        validation_issues.append({'doc': doc_name, 'claim': claim, **res})
                except:
                    continue # Skip if it fails to parse to save time/tokens
        
        return {"issues": validation_issues, "count": len(validation_issues)}

    def _extract_claims(self, doc_content: str) -> List[str]:
        """Strictly filter for high-value claims only."""
        sentences = doc_content.split('.')
        # Only look for hard implementation claims
        keywords = ['implements', 'uses', 'requires', 'built with']
        return [s.strip() for s in sentences if any(k in s.lower() for k in keywords) and 20 < len(s) < 150]