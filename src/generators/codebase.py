"""GitHub codebase selector and describer for odgsully repositories."""
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

from ..settings import settings
from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
CODEBASE_HISTORY_FILE = "codebase_history.json"


@dataclass
class Repository:
    """Represents a GitHub repository."""
    name: str
    full_name: str
    description: Optional[str]
    url: str
    language: Optional[str]
    stars: int
    created_at: str
    updated_at: str
    private: bool
    size: int
    default_branch: str
    topics: List[str]


class CodebaseSelector:
    """Selects and describes odgsully GitHub repositories."""
    
    def __init__(self, username: str = "odgsully"):
        """Initialize the codebase selector.
        
        Args:
            username: GitHub username to fetch repos from
        """
        self.username = username
        self.history_file = settings.root_dir / CODEBASE_HISTORY_FILE
        self.headers = {}
        
        if settings.github_token:
            self.headers["Authorization"] = f"token {settings.github_token}"
            
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self.headers
        )
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def _load_history(self) -> List[str]:
        """Load codebase selection history.
        
        Returns:
            List of previously selected repository names
        """
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return data.get("history", [])
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                return []
        return []
    
    def _save_history(self, history: List[str]) -> None:
        """Save codebase selection history.
        
        Args:
            history: List of repository names
        """
        try:
            with open(self.history_file, 'w') as f:
                json.dump({"history": history}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_user_repos(self) -> List[Repository]:
        """Fetch all repositories for the user.
        
        Returns:
            List of Repository objects
        """
        repos = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{GITHUB_API_BASE}/users/{self.username}/repos"
            params = {
                "page": page,
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
                
            for repo_data in data:
                repo = Repository(
                    name=repo_data["name"],
                    full_name=repo_data["full_name"],
                    description=repo_data.get("description", ""),
                    url=repo_data["html_url"],
                    language=repo_data.get("language"),
                    stars=repo_data.get("stargazers_count", 0),
                    created_at=repo_data["created_at"],
                    updated_at=repo_data["updated_at"],
                    private=repo_data.get("private", False),
                    size=repo_data.get("size", 0),
                    default_branch=repo_data.get("default_branch", "main"),
                    topics=repo_data.get("topics", [])
                )
                repos.append(repo)
            
            if len(data) < per_page:
                break
                
            page += 1
        
        logger.info(f"Fetched {len(repos)} repositories for {self.username}")
        return repos
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_readme_content(self, repo: Repository) -> Optional[str]:
        """Fetch README content from a repository.
        
        Args:
            repo: Repository to fetch README from
            
        Returns:
            README content if found, None otherwise
        """
        # Common README filenames
        readme_names = ["README.md", "README.txt", "README.rst", "README", "readme.md", "readme.txt"]
        
        for readme_name in readme_names:
            try:
                url = f"{GITHUB_API_BASE}/repos/{repo.full_name}/contents/{readme_name}"
                response = await self.client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("encoding") == "base64":
                        import base64
                        content = base64.b64decode(data["content"]).decode('utf-8')
                        logger.info(f"Found README: {readme_name} for {repo.name}")
                        return content
                        
            except Exception as e:
                logger.debug(f"Could not fetch {readme_name}: {e}")
                continue
        
        logger.info(f"No README found for {repo.name}")
        return None

    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_repo_structure(self, repo: Repository) -> str:
        """Fetch the directory structure of a repository.
        
        Args:
            repo: Repository to fetch structure for
            
        Returns:
            Formatted directory structure string
        """
        url = f"{GITHUB_API_BASE}/repos/{repo.full_name}/contents"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            contents = response.json()
            
            # Build directory structure
            structure_lines = [f"Repository: {repo.name}"]
            structure_lines.append("=" * 40)
            structure_lines.append("")
            
            # Sort contents by type (dirs first) then name
            contents.sort(key=lambda x: (x["type"] != "dir", x["name"]))
            
            for item in contents:
                if item["type"] == "dir":
                    structure_lines.append(f"📁 {item['name']}/")
                else:
                    structure_lines.append(f"📄 {item['name']}")
            
            return "\n".join(structure_lines)
            
        except Exception as e:
            logger.error(f"Failed to fetch repo structure: {e}")
            return f"Repository: {repo.name}\n(Unable to fetch directory structure)"
    
    def select_repository(self, repos: List[Repository]) -> Repository:
        """Select a repository avoiding recent repetitions.
        
        Args:
            repos: List of available repositories
            
        Returns:
            Selected repository
        """
        if not repos:
            raise ValueError("No repositories available")
        
        # Load history
        history = self._load_history()
        
        # If only one repo or no history, just pick the first
        if len(repos) == 1 or not history:
            selected = repos[0]
        else:
            # Try to find a repo not in recent history
            available_repos = [r for r in repos if r.name not in history[-2:]]
            
            # If all repos are recent, just use all repos
            if not available_repos:
                available_repos = repos
            
            # Select randomly from available
            selected = random.choice(available_repos)
        
        # Update history
        history.append(selected.name)
        # Keep only last 10 selections
        if len(history) > 10:
            history = history[-10:]
        self._save_history(history)
        
        logger.info(f"Selected repository: {selected.name}")
        return selected
    
    async def get_codebase_of_the_day(self) -> Tuple[str, str]:
        """Get the codebase of the day with its summary.
        
        Returns:
            Tuple of (repository_name, summary)
        """
        try:
            # Import here to avoid circular import
            from .summariser import Summarizer
            
            # Fetch all repositories
            repos = await self.fetch_user_repos()
            
            if not repos:
                return "(No repositories found)", "(No summary available)"
            
            # Select repository
            selected_repo = self.select_repository(repos)
            
            # Fetch directory structure and README
            structure = await self.fetch_repo_structure(selected_repo)
            readme_content = await self.fetch_readme_content(selected_repo)
            
            # Build comprehensive summary
            summary_parts = []
            
            # Basic info
            if selected_repo.description:
                summary_parts.append(f"Description: {selected_repo.description}")
            
            if selected_repo.language:
                summary_parts.append(f"Primary Language: {selected_repo.language}")
            
            summary_parts.append(f"Stars: {selected_repo.stars}")
            summary_parts.append(f"Size: {selected_repo.size} KB")
            
            if selected_repo.topics:
                summary_parts.append(f"Topics: {', '.join(selected_repo.topics)}")
            
            # Add README summary if available
            if readme_content:
                try:
                    summarizer = Summarizer()
                    readme_summary = await summarizer.summarize(
                        readme_content, 
                        "codebase_summary", 
                        150
                    )
                    summary_parts.append("")
                    summary_parts.append("README Summary:")
                    summary_parts.append(readme_summary)
                except Exception as e:
                    logger.error(f"Failed to summarize README: {e}")
                    summary_parts.append("")
                    summary_parts.append("README found but summary failed")
            
            summary_parts.append("")
            summary_parts.append("Directory Structure:")
            summary_parts.append(structure)
            
            summary = "\n".join(summary_parts)
            
            return selected_repo.name, summary
            
        except Exception as e:
            logger.error(f"Failed to get codebase of the day: {e}")
            return "(Codebase selection error)", f"(Error: {str(e)})"