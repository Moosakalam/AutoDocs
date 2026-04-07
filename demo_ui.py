"""
AutoDoc Showcase Web UI
Interactive Streamlit interface for demonstrating the AutoDoc multi-agent pipeline.
"""
# --- CHROMADB STREAMLIT CLOUD HACK ---
import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
# -------------------------------------

import streamlit as st
import asyncio
from pathlib import Path
# ... the rest of your code continues normally ...
import streamlit as st
import asyncio
from pathlib import Path
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AutoDoc - AI Documentation", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 3rem; font-weight: bold; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; text-align: center; color: #666; margin-bottom: 2rem; }
    .metric-card { background-color: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem; text-align: center; border: 1px solid #e9ecef; border-left: 4px solid #1f77b4;}
    .metric-value { font-size: 2rem; font-weight: bold; color: #1f77b4; }
    .metric-label { font-size: 1rem; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }
    .cta-box { background-color: #e8f4f8; padding: 1rem; border-radius: 0.5rem; border: 1px solid #1f77b4; text-align: center; margin-top: 1rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🤖 AutoDoc</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous Multi-Agent Codebase Documentation</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")
    input_method = st.radio("Input Method", ["GitHub URL", "Local Path", "Demo Project"])
    
    if input_method == "Local Path":
        repo_path = st.text_input("Repository Path", placeholder="/path/to/your/project")
        repo_url = None
    elif input_method == "GitHub URL":
        repo_url = st.text_input("GitHub URL", placeholder="https://github.com/Moosakalam/ai-geopolitics-newsroom")
        repo_path = None
    else:
        repo_path = "./demo_project"
        repo_url = None
        st.info("Using pre-configured local demo project.")
    
    st.divider()
    run_button = st.button("🚀 Run AutoDoc Pipeline", type="primary", use_container_width=True)

tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📂 Browse Generated Files", "🏗️ Architecture"])

# --- HELPER FUNCTION TO RENDER DASHBOARD ---
def render_dashboard_insights(output_dir: Path):
    """Reads the JSON reports and builds a rich UI dashboard."""
    quality_file = output_dir / "quality_review.json"
    analysis_file = output_dir / "analysis_report.json"
    
    if not quality_file.exists() or not analysis_file.exists():
        st.info("Run the pipeline or load a previously processed repository to see deep insights here!")
        return

    try:
        with open(quality_file, 'r') as f:
            quality_data = json.load(f)
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
            
        # Safely extract evaluation data 
        eval_data = quality_data.get('evaluation', quality_data.get('scores', {}))
        overall_score = eval_data.get('overall_quality', eval_data.get('overall', 'N/A'))
        coverage_data = quality_data.get('coverage', {})
        val_summary = quality_data.get('validation_summary', {})

        # 1. Top Level Metrics
        st.markdown("### 📈 Pipeline Results")
        c1, c2, c3, c4 = st.columns(4)
        
        c1.markdown(f'<div class="metric-card"><div class="metric-value">{overall_score}/10</div><div class="metric-label">Quality Score</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-value">{coverage_data.get("coverage_percentage", 0)}%</div><div class="metric-label">Doc Coverage</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-value">{coverage_data.get("total_code_chunks", 0)}</div><div class="metric-label">Code Chunks Analyzed</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><div class="metric-value">{val_summary.get("issues", 0)}</div><div class="metric-label">Issues Detected</div></div>', unsafe_allow_html=True)
        
        # --- NEW CTA TO GUIDE USERS TO TAB 2 ---
        st.markdown(
            '<div class="cta-box"><h4>✨ Documentation is ready! Click the <b>"📂 Browse Generated Files"</b> tab above to read your new README and guides.</h4></div>', 
            unsafe_allow_html=True
        )
        st.divider()

        # 2. Deep Insights (Strengths & Weaknesses)
        colA, colB = st.columns(2)
        with colA:
            st.success("#### 🌟 Key Strengths")
            for strength in quality_data.get('strengths', ['No strengths identified.']):
                st.write(f"- {strength}")
                
            st.info("#### 💡 Recommendations")
            for rec in quality_data.get('recommendations', ['No recommendations available.']):
                st.write(f"- {rec}")

        with colB:
            st.warning("#### ⚠️ Areas for Improvement")
            for weakness in quality_data.get('weaknesses', ['No areas for improvement identified.']):
                st.write(f"- {weakness}")
                
            st.markdown("#### 🧩 Detected Architecture")
            st.write(f"**Type:** {analysis_data.get('architecture_type', 'Unknown').title()}")
            with st.expander("View Detected Design Patterns"):
                for pattern in analysis_data.get('design_patterns', []):
                    st.write(f"- {pattern}")
    except Exception as e:
        st.error(f"Error reading dashboard data: {e}")

# --- TAB 1: EXECUTION & DASHBOARD ---
with tab1:
    progress_placeholder = st.empty()
    
    if run_button:
        with st.spinner("🔄 Initializing AutoDoc System..."):
            progress_bar = progress_placeholder.progress(0)
            try:
                if not repo_url and not repo_path:
                    st.error("❌ Please provide a valid GitHub URL or Local Path.")
                    st.stop()

                st.info("📥 Deploying Agents & Parsing Code...")
                progress_bar.progress(25)
                
                sys.path.insert(0, str(Path(__file__).parent / "src"))
                from orchestration.workflow import AutoDocOrchestrator
                import yaml
                
                with open('config/config.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                
                orchestrator = AutoDocOrchestrator(config)
                
                st.info("🚀 Agents analyzing architecture and writing docs... (This takes a few minutes)")
                progress_bar.progress(60)
                
                output_dir = "./demo_output"
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    orchestrator.run_full_pipeline(repo_url=repo_url, repo_path=repo_path, output_dir=output_dir)
                )
                
                progress_bar.progress(100)
                st.success("✅ Multi-Agent Documentation Complete!")
                progress_placeholder.empty()
                
            except Exception as e:
                st.error(f"❌ Pipeline Error: {e}")
                st.stop()

    # Always attempt to render the dashboard if files exist
    render_dashboard_insights(Path("./demo_output"))

# --- TAB 2: OUTPUT VIEWER ---
with tab2:
    st.header("📂 Document Explorer")
    st.markdown("""
    **Your agents have successfully drafted full documentation.** Use the dropdown menu below to select a file and view its contents live, or download it to your local machine.
    """)
    st.divider()
    
    output_dir = Path("./demo_output")
    
    if output_dir.exists():
        files = list(output_dir.glob("*.md")) + list(output_dir.glob("*.json"))
        if files:
            # Sort files so README is usually near the top
            file_names = sorted([f.name for f in files], key=lambda x: (not x.startswith('README'), x))
            
            selected_file = st.selectbox(
                "👇 Select a generated document to read:", 
                file_names,
                help="Choose between Markdown files (README, Module Guide) or raw JSON metric reports."
            )
            
            if selected_file:
                file_path = output_dir / selected_file
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Add a download button right next to the file title
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(f"Viewing: `{selected_file}`")
                with col2:
                    st.download_button(label="📥 Download File", data=content, file_name=selected_file, mime="text/plain", use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True) # visual spacing
                
                with st.container(border=True):
                    if selected_file.endswith('.json'):
                        try:
                            st.json(json.loads(content))
                        except:
                            st.code(content, language='json')
                    else:
                        st.markdown(content)
        else:
            st.info("No documentation generated yet. Head back to the Dashboard to run the pipeline!")
    else:
        st.info("No output directory found. Run AutoDoc first to view results here.")

# --- TAB 3: ABOUT ---
with tab3:
    st.header("🏗️ How AutoDoc Works")
    st.markdown("""
    AutoDoc uses 5 specialized AI agents orchestrated with AutoGen and ChromaDB to autonomously ingest code, map architecture, and write validated documentation.
    - **Ingestion:** Parses code into semantic chunks via Tree-sitter.
    - **Analysis:** Identifies patterns (Factory, Singleton, etc.).
    - **Writer:** Drafts `README.md` and module guides.
    - **QA:** Cross-references written claims against the vector store to prevent hallucinations.
    - **Reviewer:** Scores output on clarity, completeness, and accuracy.
    """)