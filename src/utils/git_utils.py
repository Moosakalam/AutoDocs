"""
Git utilities for cloning and managing repositories.
"""
import git
from pathlib import Path
import shutil

class GitUtils:
    """Utility class for Git operations."""
    
    @staticmethod
    def clone_repository(repo_url: str, target_dir: str, depth: int = 1) -> str:
        """
        Clone a Git repository.
        
        Args:
            repo_url: GitHub repository URL
            target_dir: Directory to clone into
            depth: Clone depth (1 for shallow clone)
        
        Returns:
            Path to cloned repository
        """
        target_path = Path(target_dir)
        
        # Remove existing directory if it exists
        if target_path.exists():
            shutil.rmtree(target_path)
        
        print(f"Cloning {repo_url} into {target_dir}...")
        git.Repo.clone_from(repo_url, target_dir, depth=depth)
        print(f"Repository cloned successfully to {target_dir}")
        
        return target_dir
    
    @staticmethod
    def get_repo_metadata(repo_path: str) -> dict:
        """
        Extract metadata from cloned repository.
        
        Args:
            repo_path: Path to repository
        
        Returns:
            Dictionary with repo metadata
        """
        try:
            repo = git.Repo(repo_path)
            return {
                'remote_url': repo.remotes.origin.url if repo.remotes else None,
                'active_branch': repo.active_branch.name,
                'latest_commit': repo.head.commit.hexsha[:8],
                'commit_message': repo.head.commit.message.strip(),
                'author': str(repo.head.commit.author)
            }
        except Exception as e:
            return {'error': str(e)}