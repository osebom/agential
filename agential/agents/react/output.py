"""ReAct structured output module."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from agential.core.base.agents.output import BaseAgentOutput
from agential.llm.llm import Response


class ReActStepOutput(BaseModel):
    """ReAct step Pydantic output class.

    Attributes:
        thought (str): The thought process of the agent.
        action_type (str): The type of action performed by the agent.
        query (str): The query requested by the agent.
        observation (str): The observation made by the agent.
        answer (str): The answer generated by the agent.
        external_tool_info (Dict[str, Any]): The external tool outputs.
        thought_response (Response): The thought response including input/output text, token usage, cost, and latency.
        action_response (Response): The action response including input/output text, token usage, cost, and latency.
    """

    thought: str = Field(..., description="The thought process of the agent.")
    action_type: str = Field(
        ..., description="The type of action performed by the agent."
    )
    query: str = Field(..., description="The query requested by the agent.")
    observation: str = Field(..., description="The observation made by the agent.")
    answer: str = Field(..., description="The answer generated by the agent.")
    external_tool_info: Dict[str, Any] = Field(
        ..., description="The external tool outputs."
    )
    thought_response: Response = Field(
        ...,
        description="The thought response including input/output text, token usage, cost, and latency.",
    )
    action_response: Response = Field(
        ...,
        description="The action response including input/output text, token usage, cost, and latency.",
    )


class ReActOutput(BaseAgentOutput):
    """ReAct structured output class.

    Attributes:
        additional_info (List[ReActStepOutput]): The list of ReAct step outputs.
    """

    additional_info: List[ReActStepOutput] = Field(
        ..., description="The list of ReActStepOutput."
    )
