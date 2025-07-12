"""Template engine for rendering daily briefings using Jinja2."""
import random
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from .settings import settings
from .utils.logger import get_logger

logger = get_logger(__name__)


class TemplateEngine:
    """Handles template rendering with Jinja2."""
    
    def __init__(self):
        """Initialize the template engine."""
        self.env = Environment(
            loader=FileSystemLoader(settings.templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Load rotation phrases
        self.get_to_it_phrases = [
            "dive into",
            "take a glance at",
            "explore",
            "breakdown",
            "examine",
            "check out",
            "review",
            "analyze",
            "inspect",
            "look at",
        ]
        
        # Add custom filters
        self.env.filters['rotate_phrase'] = self._rotate_phrase
        
    def _rotate_phrase(self, phrase_list: List[str], seed: str = None) -> str:
        """Rotate through a list of phrases deterministically.
        
        Args:
            phrase_list: List of phrases to choose from
            seed: Optional seed for deterministic selection
            
        Returns:
            Selected phrase
        """
        if not phrase_list:
            return ""
            
        if seed:
            # Use seed for deterministic selection
            random.seed(seed)
            choice = random.choice(phrase_list)
            random.seed()  # Reset random seed
            return choice
        else:
            return random.choice(phrase_list)
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of template variables
            
        Returns:
            Rendered template string
        """
        try:
            # Add rotation phrases to context
            context['GET_TO_IT_SAYING'] = self._rotate_phrase(
                self.get_to_it_phrases,
                seed=context.get('FULLDATE', '')
            )
            
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            
            logger.info(
                "Template rendered successfully",
                template=template_name,
                context_keys=list(context.keys()),
            )
            
            return rendered
            
        except Exception as e:
            logger.error(
                "Failed to render template",
                template=template_name,
                error=str(e),
            )
            raise
    
    def get_template_variables(self, template_name: str) -> List[str]:
        """Extract all variables from a template.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            List of variable names found in the template
        """
        try:
            template_source = self.env.loader.get_source(self.env, template_name)[0]
            template = self.env.parse(template_source)
            
            variables = set()
            for node in template.find_all():
                if hasattr(node, 'name'):
                    variables.add(node.name)
                    
            return sorted(list(variables))
            
        except Exception as e:
            logger.error(
                "Failed to extract template variables",
                template=template_name,
                error=str(e),
            )
            return []
    
    def validate_context(self, template_name: str, context: Dict[str, Any]) -> List[str]:
        """Validate that all required template variables are provided.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of template variables
            
        Returns:
            List of missing variable names
        """
        required_vars = self.get_template_variables(template_name)
        provided_vars = set(context.keys())
        
        missing_vars = [var for var in required_vars if var not in provided_vars]
        
        if missing_vars:
            logger.warning(
                "Missing template variables",
                template=template_name,
                missing=missing_vars,
            )
            
        return missing_vars