"""
AutoDoc Orchestration Layer
Coordinates all 5 agents using AutoGen v0.4+ workflow
"""
 
import asyncio
from typing import Dict
import json
import os
from pathlib import Path
 
# Import all components
from src.utils.file_utils import FileUtils
from src.utils.git_utils import GitUtils
from src.rag.vector_store import VectorStore
from src.rag.retriever import CodeRetriever
from src.parsers.code_parser import CodeParser
from agents.ingestion_agent import IngestionAgent
from agents.analysis_agent import AnalysisAgent
from agents.writer_agent import WriterAgent
from agents.qa_agent import QAAgent
from agents.reviewer_agent import ReviewerAgent
 
 
class AutoDocOrchestrator:
    """
    Main orchestrator for AutoDoc system.
    Coordinates all 5 agents in sequential workflow.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        
        # Initialize core components
        print("🚀 Initializing AutoDoc System...")
        
        # RAG Components
        self.vector_store = VectorStore(
            persist_directory=config['chromadb']['persist_directory'],
            collection_name=config['chromadb']['collection_name']
        )
        self.retriever = CodeRetriever(self.vector_store)
        
        # Parsing Components
        self.code_parser = CodeParser()
        self.file_utils = FileUtils()
        self.git_utils = GitUtils()
        
        # LLM Configuration
        self.llm_config = config['llm']
        
        # Initialize Agents
        print("🤖 Initializing agents...")
        self.ingestion_agent = IngestionAgent(
            self.code_parser,
            self.vector_store,
            self.file_utils
        )
        
        self.analysis_agent = AnalysisAgent(
            self.retriever,
            self.llm_config
        )
        
        self.writer_agent = WriterAgent(
            self.retriever,
            self.llm_config
        )
        
        self.qa_agent = QAAgent(
            self.retriever,
            self.llm_config
        )
        
        self.reviewer_agent = ReviewerAgent(
            self.retriever,
            self.vector_store,
            self.llm_config
        )
        
        print("✅ All agents initialized")
    
    async def run_full_pipeline(self, repo_url: str = None, 
                               repo_path: str = None,
                               output_dir: str = "./output") -> Dict:
        """
        Execute complete AutoDoc pipeline.
        
        Args:
            repo_url: GitHub repository URL (if cloning)
            repo_path: Local repository path (if already cloned)
            output_dir: Directory to save generated documentation
        
        Returns:
            Complete pipeline results
        """
        print("\n" + "="*80)
        print("🎯 AUTODOC PIPELINE STARTED")
        print("="*80)
        
        results = {}
        
        # STEP 1: Repository Preparation
        if repo_url:
            print("\n📥 STEP 1: Cloning repository...")
            repo_path = self.git_utils.clone_repository(
                repo_url,
                "./temp_repo",
                depth=self.config['repository']['clone_depth']
            )
            repo_metadata = self.git_utils.get_repo_metadata(repo_path)
            results['repo_metadata'] = repo_metadata
        elif repo_path:
            print(f"\n📂 STEP 1: Using local repository: {repo_path}")
            repo_metadata = self.git_utils.get_repo_metadata(repo_path)
            results['repo_metadata'] = repo_metadata
        else:
            raise ValueError("Must provide either repo_url or repo_path")
        
        # STEP 2: Ingestion (Agent 1)
        print("\n🔍 STEP 2: Code Ingestion & Embedding...")
        ingestion_report = self.ingestion_agent.ingest_repository(
            repo_path=repo_path,
            exclude_patterns=self.config['repository']['exclude_patterns']
        )
        results['ingestion_report'] = ingestion_report
        
        # STEP 3: Analysis (Agent 2)
        print("\n🧠 STEP 3: Codebase Analysis...")
        analysis_report = await self.analysis_agent.analyze_codebase(repo_metadata)
        results['analysis_report'] = analysis_report
        
        # Save intermediate analysis
        self._save_json(analysis_report, output_dir, "analysis_report.json")
        
        # STEP 4: Documentation Generation (Agent 3)
        print("\n📝 STEP 4: Generating Documentation...")
        documentation = await self.writer_agent.generate_documentation(
            analysis_report=analysis_report,
            repo_metadata=repo_metadata
        )
        results['documentation'] = documentation
        
        # Save documentation files
        for filename, content in documentation.items():
            self._save_file(content, output_dir, filename)
        
        # STEP 5: Quality Assurance (Agent 4)
        print("\n✅ STEP 5: Validating Documentation...")
        validation_report = await self.qa_agent.validate_documentation(
            docs=documentation,
            analysis_report=analysis_report
        )
        results['validation_report'] = validation_report
        
        # Save validation report
        self._save_json(validation_report, output_dir, "validation_report.json")
        
        # STEP 6: Final Review (Agent 5)
        print("\n⭐ STEP 6: Quality Review...")
        quality_review = await self.reviewer_agent.review_documentation(
            docs=documentation,
            validation_report=validation_report,
            analysis_report=analysis_report
        )
        results['quality_review'] = quality_review
        
        # Save quality review
        self._save_json(quality_review, output_dir, "quality_review.json")
        
        # Generate Final Report
        print("\n📊 Generating Final Report...")
        final_report = self._generate_final_report(results)
        self._save_file(final_report, output_dir, "AUTODOC_REPORT.md")
        
        print("\n" + "="*80)
        print("✨ AUTODOC PIPELINE COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"\n📁 Documentation saved to: {output_dir}")
        print(f"   - README.md")
        print(f"   - MODULE_GUIDE.md")
        print(f"   - ONBOARDING.md")
        print(f"   - AUTODOC_REPORT.md")
        print(f"   - analysis_report.json")
        print(f"   - validation_report.json")
        print(f"   - quality_review.json")
        
        return results
    
    def _save_file(self, content: str, output_dir: str, filename: str):
        """Save content to file."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(output_dir) / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Saved: {filename}")
    
    def _save_json(self, data: Dict, output_dir: str, filename: str):
        """Save JSON data to file."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(output_dir) / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ Saved: {filename}")
    
    def _generate_final_report(self, results: Dict) -> str:
        """Generate markdown summary report handling dynamic keys."""
        
        quality = results.get('quality_review', {})
        # Safely extract scores handling both the old 'scores' and new 'evaluation' keys
        scores = quality.get('evaluation', quality.get('scores', {}))
        
        validation = results.get('validation_report', {})
        ingestion = results.get('ingestion_report', {})
        coverage = quality.get('coverage', {})
        
        # Safely extract validation counts
        val_count = validation.get('count', validation.get('total_claims_checked', 'N/A'))
        val_issues_count = validation.get('issues_found', len(validation.get('issues', [])))
        
        # Safely extract specific scores
        overall_score = scores.get('overall_quality', scores.get('overall', 'N/A'))
        
        # Safely format coverage percentage
        cov_pct = coverage.get('coverage_percentage', 'N/A')
        cov_str = f"{cov_pct:.1f}%" if isinstance(cov_pct, (int, float)) else str(cov_pct)

        report = f"""# AutoDoc Final Report
Generated: {self._get_timestamp()}
 
## Executive Summary
 
**Overall Quality Score:** {overall_score}/10
 
### Quality Breakdown
- **Completeness:** {scores.get('completeness', 'N/A')}/10
- **Clarity:** {scores.get('clarity', 'N/A')}/10
- **Accuracy:** {scores.get('accuracy', 'N/A')}/10
- **Structure:** {scores.get('structure', 'N/A')}/10
- **Usefulness:** {scores.get('usefulness', 'N/A')}/10
 
---
 
## Codebase Metrics
 
### Ingestion Statistics
- **Total Files Processed:** {ingestion.get('total_files', 'N/A')}
- **Total Code Chunks:** {ingestion.get('total_chunks', 'N/A')}
- **Languages Detected:** {', '.join(ingestion.get('languages', [])) if ingestion.get('languages') else 'N/A'}
 
### Chunk Distribution
- **Functions:** {ingestion.get('chunk_types', {}).get('functions', 0)}
- **Classes:** {ingestion.get('chunk_types', {}).get('classes', 0)}
- **Line Chunks:** {ingestion.get('chunk_types', {}).get('line_chunks', 0)}
 
---
 
## Validation Results
 
### QA Summary
- **Claims Validated:** {val_count}
- **Issues Detected:** {val_issues_count}
- **Critical Issues:** {validation.get('critical_issues', 0)}
- **Major Issues:** {validation.get('major_issues', 0)}
 
### Coverage
- **Documentation Coverage:** {cov_str}
- **Files Generated:** {coverage.get('files_generated', 'N/A')}
 
---
 
## Strengths
 
{self._format_list(quality.get('strengths', []))}
 
---
 
## Areas for Improvement
 
{self._format_list(quality.get('weaknesses', []))}
 
---
 
## Recommendations
 
{self._format_list(quality.get('recommendations', []))}
 
---
 
## Critical Issues to Address
 
"""
        
        # Add critical issues if any
        critical_issues = [
            issue for issue in validation.get('issues', [])
            if issue.get('severity') == 'critical'
        ]
        
        if critical_issues:
            for i, issue in enumerate(critical_issues, 1):
                report += f"\n### Issue {i}: {issue.get('claim', 'Unknown')[:100]}\n"
                report += f"- **Status:** {issue.get('status', 'N/A')}\n"
                report += f"- **Suggestion:** {issue.get('suggestion', 'N/A')}\n"
        else:
            report += "\n✅ No critical issues detected.\n"
        
        report += "\n---\n\n"
        report += "**Generated by AutoDoc** - Multi-Agent Documentation System\n"
        
        return report
    
    def _format_list(self, items: list) -> str:
        """Format list items as markdown."""
        if not items:
            return "_None identified_"
        return "\n".join(f"- {item}" for item in items)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")