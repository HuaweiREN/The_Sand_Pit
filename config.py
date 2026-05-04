"""
The Sand Pit - Configuration Module
Core configuration dataclasses and global config loader.
"""

import json
import os
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class TurnOrderMode(Enum):
    """Turn ordering strategy."""
    RANDOM = "random"       # Random first actor each round
    ALTERNATING = "alternating"  # First actor alternates every round


@dataclass
class APIConfig:
    """API connection configuration."""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    timeout: int = 30
    client_type: str = "auto"  # "auto" | "openai" | "anthropic"


@dataclass
class WorldConfig:
    """World / arena parameters."""
    map_size: int = 50              # Map size (NxN grid)
    max_rounds: int = 50            # Max rounds per game (hard limit)
    turn_order_mode: TurnOrderMode = TurnOrderMode.ALTERNATING


@dataclass
class PhysicsConfig:
    """Physics constants (asymmetric by design)."""
    perception_radius: float = 10.0     # R_p: perception radius
    move_step: float = 3.0              # S: max movement per turn
    capture_radius: float = 0.5         # R_c: Agent A capture radius
    agent_b_capture_radius: float = 3.0 # Agent B capture radius (asymmetric)


@dataclass
class ExperimentConfig:
    """Experiment variables (the manipulated parameter)."""
    token_budget: int = 400             # B_t: token budget, mapped to max_tokens
    prompt_strategy: str = "standard"   # "minimal" | "standard"
    num_runs: int = 10                  # Batch size per experiment


@dataclass
class LoggingConfig:
    """Logging settings."""
    log_dir: str = "logs"
    log_level: str = "INFO"
    save_prompts: bool = True
    save_responses: bool = True


@dataclass
class VisualizationConfig:
    """Visualization / replay settings."""
    cell_size: int = 15                 # Grid cell size in pixels
    update_interval: int = 1000         # Default refresh interval (ms)
    show_perception_shadow: bool = True
    theme: str = "dark"                 # "dark" | "light"


class Config:
    """
    Global configuration singleton.
    Single entry point for all system configuration.
    """

    def __init__(self, config_file: Optional[str] = None):
        self.api = APIConfig()
        self.world = WorldConfig()
        self.physics = PhysicsConfig()
        self.experiment = ExperimentConfig()
        self.logging = LoggingConfig()
        self.visualization = VisualizationConfig()
        self.prompt_templates: Optional[dict] = None
        self.spawn_points: Optional[dict] = None

        # Wall configuration: a vertical wall between (25,10) and (26,48)
        self.walls: List[Dict[str, Any]] = [
            {
                'x1': 25.0, 'y1': 10.0, 'x2': 26.0, 'y2': 48.0,
                'description': 'Wall from (25,10) to (26,48). Agents cannot pass through.'
            }
        ]

        # Load API config from environment variables
        self._load_from_env()

        # Load from file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

    def _load_from_env(self):
        """Load sensitive config from environment variables.

        Supported env vars:
        - OPENAI_API_KEY / ANTHROPIC_AUTH_TOKEN: API key
        - OPENAI_BASE_URL / ANTHROPIC_BASE_URL: Base URL
        - MODEL_NAME / ANTHROPIC_MODEL: Model name
        """
        self.api.api_key = os.getenv("OPENAI_API_KEY") or \
                          os.getenv("ANTHROPIC_AUTH_TOKEN") or \
                          self.api.api_key

        self.api.base_url = os.getenv("OPENAI_BASE_URL") or \
                           os.getenv("ANTHROPIC_BASE_URL") or \
                           self.api.base_url

        self.api.model_name = os.getenv("MODEL_NAME") or \
                             os.getenv("ANTHROPIC_MODEL") or \
                             os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL") or \
                             self.api.model_name

    def _load_from_file(self, config_file: str):
        """Load configuration from a JSON file."""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'api' in data:
            for k, v in data['api'].items():
                if hasattr(self.api, k):
                    setattr(self.api, k, v)

        if 'world' in data:
            for k, v in data['world'].items():
                if hasattr(self.world, k):
                    if k == 'turn_order_mode':
                        setattr(self.world, k, TurnOrderMode(v))
                    else:
                        setattr(self.world, k, v)

        if 'physics' in data:
            for k, v in data['physics'].items():
                if hasattr(self.physics, k):
                    setattr(self.physics, k, v)

        if 'experiment' in data:
            for k, v in data['experiment'].items():
                if hasattr(self.experiment, k):
                    setattr(self.experiment, k, v)

        if 'logging' in data:
            for k, v in data['logging'].items():
                if hasattr(self.logging, k):
                    setattr(self.logging, k, v)

        if 'visualization' in data:
            for k, v in data['visualization'].items():
                if hasattr(self.visualization, k):
                    setattr(self.visualization, k, v)

        if 'prompt_templates' in data:
            self.prompt_templates = data['prompt_templates']

        if 'spawn_points' in data:
            self.spawn_points = data['spawn_points']

        if 'walls' in data:
            self.walls = data['walls']

    def save_to_file(self, config_file: str):
        """Save configuration to a JSON file (secrets redacted)."""
        data = {
            'api': asdict(self.api),
            'world': {
                **asdict(self.world),
                'turn_order_mode': self.world.turn_order_mode.value
            },
            'physics': asdict(self.physics),
            'experiment': asdict(self.experiment),
            'logging': asdict(self.logging),
            'visualization': asdict(self.visualization)
        }
        if self.prompt_templates:
            data['prompt_templates'] = self.prompt_templates
        if self.spawn_points:
            data['spawn_points'] = self.spawn_points
        if self.walls:
            data['walls'] = self.walls
        # Redact sensitive info
        data['api']['api_key'] = '***REDACTED***'

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def validate(self) -> list[str]:
        """Validate configuration. Returns a list of error messages."""
        errors = []

        if not self.api.api_key:
            errors.append("API key is required")

        if self.world.map_size < 10 or self.world.map_size > 200:
            errors.append("map_size must be between 10 and 200")

        if self.physics.perception_radius <= 0:
            errors.append("perception_radius must be positive")

        if self.physics.move_step <= 0:
            errors.append("move_step must be positive")

        if self.physics.capture_radius <= 0:
            errors.append("capture_radius must be positive")

        if self.experiment.token_budget < 50:
            errors.append("token_budget must be at least 50")

        return errors

    @property
    def max_tokens(self) -> int:
        """Map token_budget to the API max_tokens parameter."""
        return self.experiment.token_budget

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as a dictionary."""
        return {
            'api': asdict(self.api),
            'world': {
                **asdict(self.world),
                'turn_order_mode': self.world.turn_order_mode.value
            },
            'physics': asdict(self.physics),
            'experiment': asdict(self.experiment),
            'logging': asdict(self.logging),
            'visualization': asdict(self.visualization),
            'prompt_templates': self.prompt_templates,
            'spawn_points': self.spawn_points,
            'walls': self.walls
        }


_global_config: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """Get the global configuration singleton."""
    global _global_config
    if _global_config is None:
        if config_file is None:
            default_config = Path("config.json")
            if default_config.exists():
                config_file = str(default_config)
        _global_config = Config(config_file)
    return _global_config


def reset_config():
    """Reset the global configuration singleton."""
    global _global_config
    _global_config = None
