"""Abstract base class for all content generators.

Defines the interface and common logic for generating structured content
using Claude API with validated Pydantic schemas.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Tuple, Dict, Any
from pydantic import BaseModel
from anthropic import Anthropic
from src.config import Config
from src.utils.retry import ai_retry


def _fix_schema_for_claude(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Fix schema for Claude API compatibility.

    - Add additionalProperties: false to all object types
    - Remove unsupported properties like exclusiveMinimum, exclusiveMaximum
    """
    # Properties not supported by Claude's structured output
    unsupported = {'exclusiveMinimum', 'exclusiveMaximum', 'format'}

    if isinstance(schema, dict):
        # Remove unsupported properties
        for prop in unsupported:
            schema.pop(prop, None)

        if schema.get("type") == "object":
            schema["additionalProperties"] = False

        for key, value in list(schema.items()):
            if isinstance(value, dict):
                _fix_schema_for_claude(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _fix_schema_for_claude(item)
    return schema

T = TypeVar('T', bound=BaseModel)


class BaseGenerator(ABC, Generic[T]):
    """Abstract base class for content generators using Claude structured outputs.

    All concrete generators (VideoScriptGenerator, ReadingGenerator, etc.) inherit
    from this class and implement the abstract methods for their specific content type.

    The generate() method handles the Claude API call with structured outputs,
    while subclasses define the prompts and metadata extraction logic.
    """

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize generator with Anthropic client.

        Args:
            api_key: Optional API key override. Defaults to Config.ANTHROPIC_API_KEY.
            model: Optional model override. Defaults to Config.MODEL.
        """
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return generator-specific system instructions.

        This should include:
        - Role definition (e.g., "You are an expert scriptwriter")
        - Content structure guidelines
        - Quality criteria
        - Pedagogical principles

        Returns:
            str: System prompt for Claude API
        """
        pass

    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        """Build user prompt from input parameters.

        Args:
            **kwargs: Content-specific parameters (e.g., learning_objective, topic)

        Returns:
            str: Formatted user prompt for Claude API
        """
        pass

    @abstractmethod
    def extract_metadata(self, content: T) -> dict:
        """Calculate metadata from generated content.

        This should extract metrics like:
        - word_count: Total words in content
        - estimated_duration_minutes: Time to complete/consume
        - Additional content-specific metadata

        Args:
            content: The validated Pydantic schema instance

        Returns:
            dict: Metadata dictionary with computed values
        """
        pass

    @ai_retry
    def generate(self, schema: type[T], **prompt_kwargs) -> Tuple[T, dict]:
        """Generate content using Claude structured outputs API.

        This is the main method that orchestrates:
        1. Building the user prompt from kwargs
        2. Calling Claude API with tool-based structured output
        3. Validating response with Pydantic schema
        4. Extracting metadata from validated content

        Args:
            schema: Pydantic model class for structured output validation
            **prompt_kwargs: Parameters passed to build_user_prompt()

        Returns:
            Tuple[T, dict]: (validated_content, metadata_dict)
        """
        # Build user prompt from input parameters
        user_prompt = self.build_user_prompt(**prompt_kwargs)

        # Create tool for structured output
        tool_schema = _fix_schema_for_claude(schema.model_json_schema())
        tools = [{
            "name": "output_structured",
            "description": "Output the generated content in structured format",
            "input_schema": tool_schema
        }]

        # Call Claude API with tool-based structured outputs
        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_structured"}
        )

        # Extract structured data from tool use response
        # Find the tool_use block (may not be first if there's a text block)
        content_data = None
        for block in response.content:
            if block.type == "tool_use":
                content_data = block.input
                break

        if content_data is None:
            raise ValueError(f"No tool_use block found in response. Got: {[b.type for b in response.content]}")

        # Parse and validate with Pydantic
        content = schema.model_validate(content_data)

        # Extract metadata
        metadata = self.extract_metadata(content)

        return content, metadata
