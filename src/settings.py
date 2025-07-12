"""Settings configuration using Pydantic."""
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # API Keys
    openai_api_key: str = Field(..., description="OpenAI API key")
    notion_api_key: str = Field(..., description="Notion API key")
    github_token: Optional[str] = Field(None, description="GitHub personal access token")
    
    # Email Configuration
    gmail_app_password: Optional[str] = Field(None, description="Gmail app password")
    gmail_from: str = Field("digest-bot@mycompany.com", description="Sender email")
    gmail_to: str = Field("gbsullivan@mac.com", description="Recipient email")
    
    # Application Configuration
    timezone: str = Field("America/Phoenix", description="Timezone for scheduling")
    root_dir: Path = Field(..., description="Project root directory")
    
    # Derived paths
    @property
    def outputs_dir(self) -> Path:
        """Get outputs directory path."""
        return self.root_dir / "Outputs"
    
    @property
    def dailies_dir(self) -> Path:
        """Get daily outputs directory path."""
        return self.outputs_dir / "dailies"
    
    @property
    def tables_dir(self) -> Path:
        """Get tables directory path."""
        return self.outputs_dir / "tables"
    
    @property
    def templates_dir(self) -> Path:
        """Get templates directory path."""
        return self.root_dir / "templates"
    
    @property
    def datasets_dir(self) -> Path:
        """Get datasets directory path."""
        return self.root_dir / "src" / "datasets"
    
    @property
    def transcript_dir(self) -> Path:
        """Get transcript directory path."""
        return self.root_dir / "paicc-2 copy"
    
    @field_validator("root_dir", mode="before")
    @classmethod
    def validate_root_dir(cls, v: str) -> Path:
        """Convert string to Path and validate it exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Root directory does not exist: {path}")
        return path
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for directory in [
            self.outputs_dir,
            self.dailies_dir,
            self.tables_dir,
            self.templates_dir,
            self.datasets_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()