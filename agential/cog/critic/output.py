"""CRITIC structured output module."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from agential.core.base.output import BaseOutput
from agential.llm.llm import Response


class CriticStepOutput(BaseModel):
    """Critic step Pydantic output class.

    Attributes:
        answer (str): The answer generated by the agent.
        critique (str): The critique of the answer generated by the agent.
        external_tool_info (Dict[str, Any]): The query requested by the agent.
        answer_response (List[Response]): The answer responses generated by the agent.
        critique_response (List[Response]): The critique responses generated by the agent.
    """

    answer: str = Field(..., description="The answer generated by the agent.")
    critique: str = Field(..., description="The answer's critique.")
    external_tool_info: Dict[str, Any] = Field(
        ..., description="The external tool outputs."
    )
    answer_response: List[Response] = Field(
        ..., description="The answer responses generated by the agent."
    )
    critique_response: List[Response] = Field(
        ..., description="The critique responses generated by the agent."
    )


class CriticOutput(BaseOutput):
    """Critic Pydantic output class.

    Attributes:
        additional_info (List[CriticStepOutput]): The additional info.
    """

    additional_info: List[CriticStepOutput] = Field(
        ..., description="The additional info."
    )
