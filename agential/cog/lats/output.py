"""LATS structured output module."""

from typing import List

from pydantic import BaseModel, Field
from agential.cog.lats.node import Node


class LATSSimulationOutput(BaseModel):
    """LATS simulation Pydantic output class.
    
    Attributes:

    """
    current_node: Node = Field(..., description="The current node.")
    children_nodes: List[Node] = Field(
        ...,
        description="The children nodes of the current node.",
    )
    values: List[float] = Field(
        ...,
        description="The values of the children nodes.",
    )


class LATSOutput(BaseModel):
    """LATS Pydantic output class.

    Attributes:

    """

    current_node: Node = Field(..., description="The current node.")
    children_nodes: List[Node] = Field(
        ...,
        description="The children nodes of the current node.",
    )
    values: List[float] = Field(
        ...,
        description="The values of the children nodes.",
    )
    simulation_reward:  float = Field(
        ...,
        description="The reward of the simulation from the current node's most valuable child node.",
    )
    simulation_terminal_node: Node = Field(
        ...,
        description="The terminal node of the simulation.",
    )
    simulation_results: List[LATSSimulationOutput] = Field(
        ...,
        description="The results of the simulation.",
    )

