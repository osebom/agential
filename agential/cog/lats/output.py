"""LATS structured output module."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agential.cog.base.output import BaseOutput
from agential.llm.llm import Response


class LATSReActStepOutput(BaseModel):
    """LATS ReAct Pydantic output class.

    Attributes:
        thought (str): The thought process of the agent.
        action_type (str): The type of action performed by the agent.
        query (str): The query requested by the agent.
        observation (str): The observation made by the agent.
        answer (str): The answer generated by the agent.
        external_tool_info (Dict[str, Any]): The external tool outputs.
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


class LATSGenerateResponse(BaseModel):
    """LATS generate responses Pydantic output class.

    Attributes:
        thoughts_response (List[Response]): The responses of the thoughts.
        actions_response (List[Response]): The responses of the actions.
        reflections_response (List[Response]): The responses of the reflections.
    """

    thoughts_response: List[Response] = Field(
        ...,
        description="The responses of the thoughts.",
    )

    actions_response: List[Response] = Field(
        ...,
        description="The responses of the actions.",
    )

    reflections_response: List[Response] = Field(
        ...,
        description="The responses of the reflections.",
    )


class LATSEvaluateResponse(BaseModel):
    """LATS evaluate responses Pydantic output class.

    Attributes:
        values_response (List[Optional[Response]]): The responses of the values.
    """

    values_response: List[Optional[Response]] = Field(
        ...,
        description="The responses of the values.",
    )


class LATSSimulationStepResponse(BaseModel):
    """LATS simulation step responses Pydantic output class.

    Attributes:
        generate_response (LATSGenerateResponse): The responses of the thoughts, actions, and reflections.
        evaluate_response (LATSEvaluateResponse): The responses of the values.
    """

    generate_response: LATSGenerateResponse = Field(
        ...,
        description="The responses of the thoughts, actions, and reflections.",
    )
    evaluate_response: LATSEvaluateResponse = Field(
        ...,
        description="The responses of the values.",
    )


class LATSSimulationResponse(BaseModel):
    """LATS simulation responses Pydantic output class.

    Attributes:
        simulation_step_response (List[LATSSimulationStepResponse]): The responses of the simulation.
    """

    simulation_step_response: List[LATSSimulationStepResponse] = Field(
        ...,
        description="The responses of the simulation.",
    )


class LATSSimulationOutput(BaseModel):
    """LATS simulation Pydantic output class.

    Attributes:
        simulation_reward (float): The reward of the simulation from the current node's most valuable child node.
        simulation_terminal_node (Optional[Dict[str, Any]]): The terminal node of the simulation.
        simulation_current_nodes (List[Dict[str, Any]]): The current nodes of the simulation.
        simulation_children_nodes (List[List[Dict[str, Any]]]): The children nodes of the simulation.
        simulation_values (List[List[Dict[str, Any]]]): The values of the children nodes of the simulation.
    """

    simulation_reward: float = Field(
        ...,
        description="The reward of the simulation from the current node's most valuable child node.",
    )
    simulation_terminal_node: Optional[Dict[str, Any]] = Field(
        ...,
        description="The terminal node of the simulation.",
    )
    simulation_current_nodes: List[Dict[str, Any]] = Field(
        ...,
        description="The current nodes of the simulation.",
    )
    simulation_children_nodes: List[List[Dict[str, Any]]] = Field(
        ...,
        description="The children nodes of the simulation.",
    )
    simulation_values: List[List[Dict[str, Any]]] = Field(
        ...,
        description="The values of the children nodes of the simulation.",
    )


class LATSStepOutput(BaseModel):
    """LATS Pydantic output class.

    Attributes:
        iteration (int): The iteration number.
        current_node (Dict[str, Any]): The current node.
        children_nodes (List[Dict[str, Any]]): The children nodes of the current node.
        generate_response (LATSGenerateResponse): The responses of the thoughts, actions, and reflections.
        values (Optional[List[Dict[str, Any]]]): The values of the children nodes.
        evaluate_response (Optional[LATSEvaluateResponse]): The responses of the values.
        simulation_results (Optional[LATSSimulationOutput]): The results of the simulation.
        simulation_response (Optional[LATSSimulationResponse]): The responses of the simulation.
    """

    iteration: int = Field(..., description="The iteration number.")
    current_node: Dict[str, Any] = Field(..., description="The current node.")
    children_nodes: List[Dict[str, Any]] = Field(
        ...,
        description="The children nodes of the current node.",
    )
    generate_response: LATSGenerateResponse = Field(
        ...,
        description="The responses of the thoughts, actions, and reflections.",
    )
    values: Optional[List[Dict[str, Any]]] = Field(
        ...,
        description="The values of the children nodes.",
    )
    evaluate_response: Optional[LATSEvaluateResponse] = Field(
        ...,
        description="The responses of the values.",
    )
    simulation_results: Optional[LATSSimulationOutput] = Field(
        ...,
        description="The results of the simulation.",
    )
    simulation_response: Optional[LATSSimulationResponse] = Field(
        ...,
        description="The responses of the simulation.",
    )


class LATSOutput(BaseOutput):
    """LATS Pydantic output class.

    Attributes:
        additional_info (List[LATSStepOutput]): The additional information of the LATS step output.
    """

    additional_info: List[LATSStepOutput] = Field(
        ...,
        description="The additional information of the LATS step output.",
    )
