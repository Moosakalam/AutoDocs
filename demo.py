"""
AutoDoc Quick Demo Script
Demonstrates AutoDoc on a sample project with pre-configured settings.
Always runnable for presentations and showcases.
"""

import asyncio
import os
from pathlib import Path
import shutil

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.END}\n")


def print_step(step_num, text):
    """Print step with number."""
    print(f"{Colors.CYAN}{Colors.BOLD}[{step_num}]{Colors.END} {text}")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def check_setup():
    """Check if AutoDoc is properly set up."""
    print_step(1, "Checking setup...")
    
    # Check .env file
    if not Path('.env').exists():
        print_warning(".env file not found!")
        print_info("Creating .env from template...")
        if Path('.env.example').exists():
            shutil.copy('.env.example', '.env')
            print_warning("Please edit .env and add your OPENAI_API_KEY")
            print_info("You can get a free key at: https://platform.openai.com/api-keys")
            return False
        else:
            print_warning("No .env.example found. Please create .env manually.")
            return False
    
    # Check API key
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print_warning("OPENAI_API_KEY not configured in .env")
        print_info("Please add your API key to .env file")
        return False
    
    print_success("Setup complete!")
    return True


def create_demo_project():
    """Create a sample project for demonstration."""
    print_step(2, "Creating demo project...")
    
    demo_dir = Path("./demo_project")
    demo_dir.mkdir(exist_ok=True)
    
    # Create sample Python files
    (demo_dir / "calculator.py").write_text('''"""
Simple calculator module for demonstration.
"""

class Calculator:
    """A basic calculator class."""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """
        Divide a by b.
        
        Raises:
            ValueError: If b is zero.
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
''')
    
    (demo_dir / "utils.py").write_text('''"""
Utility functions for the calculator.
"""

def validate_number(value):
    """Validate that a value is a number."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def format_result(result: float, decimals: int = 2) -> str:
    """Format calculation result for display."""
    return f"Result: {result:.{decimals}f}"


class History:
    """Keep track of calculation history."""
    
    def __init__(self):
        self.operations = []
    
    def add_operation(self, operation: str, result: float):
        """Add an operation to history."""
        self.operations.append({
            'operation': operation,
            'result': result
        })
    
    def get_history(self):
        """Get all operations."""
        return self.operations
    
    def clear(self):
        """Clear history."""
        self.operations = []
''')
    
    (demo_dir / "main.py").write_text('''"""
Main entry point for calculator application.
"""

from calculator import Calculator
from utils import validate_number, format_result, History


def main():
    """Run the calculator."""
    calc = Calculator()
    history = History()
    
    print("Simple Calculator")
    print("=" * 50)
    
    # Example operations
    result = calc.add(10, 5)
    print(format_result(result))
    history.add_operation("10 + 5", result)
    
    result = calc.multiply(3, 7)
    print(format_result(result))
    history.add_operation("3 * 7", result)
    
    print("\nHistory:")
    for op in history.get_history():
        print(f"  {op['operation']} = {op['result']}")


if __name__ == "__main__":
    main()
''')
    
    print_success("Demo project created at ./demo_project/")
    print_info("Files: calculator.py, utils.py, main.py")
    
    return str(demo_dir)


async def run_autodoc(repo_path):
    """Run AutoDoc on the demo project."""
    print_step(3, "Running AutoDoc...")
    print_info("This will take approximately 2-3 minutes...")
    print()
    
    # Import orchestrator
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    try:
        from orchestration.workflow import AutoDocOrchestrator
        import yaml
        
        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize orchestrator
        orchestrator = AutoDocOrchestrator(config)
        
        # Run pipeline
        output_dir = "./demo_output"
        results = await orchestrator.run_full_pipeline(
            repo_path=repo_path,
            output_dir=output_dir
        )
        
        return output_dir, results
        
    except Exception as e:
        print_warning(f"Error running AutoDoc: {e}")
        print_info("This might be due to missing dependencies or API issues")
        return None, None


def show_results(output_dir):
    """Show generated documentation."""
    print_step(4, "Results Summary")
    
    if not output_dir or not Path(output_dir).exists():
        print_warning("No output directory found")
        return
    
    files = list(Path(output_dir).glob("*.md")) + list(Path(output_dir).glob("*.json"))
    
    if not files:
        print_warning("No documentation files generated")
        return
    
    print_success(f"Documentation generated in: {output_dir}/")
    print()
    
    for file in sorted(files):
        size = file.stat().st_size
        print(f"  📄 {file.name:<30} ({size:>6} bytes)")
    
    print()
    print_info("View the documentation:")
    print(f"    cat {output_dir}/README.md")
    print(f"    cat {output_dir}/MODULE_GUIDE.md")
    print(f"    cat {output_dir}/ONBOARDING.md")
    print()
    
    # Show quality score if available
    quality_file = Path(output_dir) / "quality_review.json"
    if quality_file.exists():
        import json
        with open(quality_file) as f:
            quality = json.load(f)
        
        if 'scores' in quality:
            overall = quality['scores'].get('overall', 'N/A')
            print_success(f"Quality Score: {overall}/10")
        elif 'evaluation' in quality:
            overall = quality['evaluation'].get('overall_quality', 'N/A')
            print_success(f"Quality Score: {overall}/10")


async def main():
    """Main demo flow."""
    print_header("🤖 AutoDoc Quick Demo")
    
    print(f"{Colors.CYAN}This demo will:{Colors.END}")
    print("  1. Check your setup")
    print("  2. Create a sample Python project")
    print("  3. Run AutoDoc to generate documentation")
    print("  4. Show you the results")
    print()
    
    input(f"{Colors.YELLOW}Press Enter to start...{Colors.END}")
    print()
    
    # Check setup
    if not check_setup():
        print()
        print_warning("Please configure your API key and run again:")
        print(f"    python demo.py")
        return
    
    print()
    
    # Create demo project
    repo_path = create_demo_project()
    print()
    
    # Run AutoDoc
    output_dir, results = await run_autodoc(repo_path)
    print()
    
    # Show results
    show_results(output_dir)
    
    print()
    print_header("🎉 Demo Complete!")
    
    print(f"{Colors.GREEN}Next steps:{Colors.END}")
    print("  • View the generated documentation")
    print("  • Try AutoDoc on your own project:")
    print("      python main.py --repo-path /path/to/your/project")
    print("  • Read the full tutorial:")
    print("      cat COMPLETE_TUTORIAL.md")
    print()
    print(f"{Colors.CYAN}Thank you for trying AutoDoc!{Colors.END}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo cancelled.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        print(f"{Colors.YELLOW}For help, see: QUICK_REFERENCE.md{Colors.END}")