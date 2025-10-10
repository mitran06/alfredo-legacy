"""Configuration management for the application."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class ReminderRule(BaseModel):
    """Configuration for a reminder rule."""
    offset_minutes: int = Field(description="Minutes before event to remind")
    message_template: str = Field(description="Template for reminder message")
    enabled: bool = Field(default=True, description="Whether this rule is enabled")


class GoogleConfig(BaseModel):
    """Google API configuration."""
    gemini_api_key: str = Field(description="Google Gemini API key")
    calendar_mcp_path: str = Field(description="Path to Google Calendar MCP server")
    oauth_credentials_path: str = Field(description="Path to OAuth credentials JSON")
    primary_calendar_id: str = Field(default="primary", description="Primary calendar ID")


class RemindersConfig(BaseModel):
    """Reminders service configuration."""
    enabled: bool = Field(default=True, description="Whether reminders are enabled")
    check_interval_seconds: int = Field(default=300, description="Interval to check for events")
    default_rules: List[ReminderRule] = Field(default_factory=list, description="Default reminder rules")


class ConversationConfig(BaseModel):
    """Conversation management configuration."""
    max_history: int = Field(default=50, description="Maximum messages to keep in history")
    context_window: int = Field(default=10, description="Number of recent messages for context")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model to use")


class TerminalConfig(BaseModel):
    """Terminal UI configuration."""
    prompt: str = Field(default="You: ", description="User input prompt")
    assistant_prefix: str = Field(default="Assistant: ", description="Assistant message prefix")
    log_prefix: str = Field(default="[LOG]", description="Log message prefix")
    show_timestamps: bool = Field(default=True, description="Whether to show timestamps")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(message)s", description="Log message format")
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Date format for logs")


class AppConfig(BaseModel):
    """Application configuration."""
    google: GoogleConfig
    reminders: RemindersConfig
    conversation: ConversationConfig
    terminal: TerminalConfig
    logging: LoggingConfig


def expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in configuration data.
    
    Supports ${VAR} and ${VAR:default} syntax.
    """
    if isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Handle ${VAR:default} syntax
        if data.startswith("${") and data.endswith("}"):
            var_part = data[2:-1]
            if ":" in var_part:
                var_name, default_value = var_part.split(":", 1)
                return os.getenv(var_name, default_value)
            else:
                var_name = var_part
                return os.getenv(var_name, data)
        return data
    else:
        return data


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config YAML file. Defaults to config/config.yaml
        
    Returns:
        AppConfig: Loaded configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    if config_path is None:
        # Default to config/config.yaml (same directory as this file)
        config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load YAML file
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Expand environment variables
    config_data = expand_env_vars(config_data)
    
    # Validate and create config object
    try:
        config = AppConfig(**config_data)
        return config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def validate_config(config: AppConfig) -> List[str]:
    """Validate that all required configuration values are present and valid.
    
    Args:
        config: Application configuration
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check Gemini API key
    if not config.google.gemini_api_key or config.google.gemini_api_key == "your_gemini_api_key_here":
        errors.append("GEMINI_API_KEY is not set or is using default value")
    
    # Check MCP server path
    mcp_path = Path(config.google.calendar_mcp_path)
    if not mcp_path.exists():
        errors.append(f"Google Calendar MCP server path does not exist: {config.google.calendar_mcp_path}")
    elif not (mcp_path / "build" / "index.js").exists():
        errors.append(f"Google Calendar MCP server not built. Run 'npm run build' in {config.google.calendar_mcp_path}")
    
    # Check OAuth credentials
    oauth_path = Path(config.google.oauth_credentials_path)
    if not oauth_path.exists():
        errors.append(f"OAuth credentials file not found: {config.google.oauth_credentials_path}")
    
    # Check reminder rules
    if config.reminders.enabled and not config.reminders.default_rules:
        errors.append("Reminders enabled but no reminder rules configured")
    
    return errors


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance.
    
    Returns:
        AppConfig: Global configuration
        
    Raises:
        RuntimeError: If configuration hasn't been loaded
    """
    global _config
    if _config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    return _config


def init_config(config_path: Optional[Path] = None) -> AppConfig:
    """Initialize the global configuration.
    
    Args:
        config_path: Path to config file (optional)
        
    Returns:
        AppConfig: Loaded configuration
    """
    global _config
    _config = load_config(config_path)
    return _config
