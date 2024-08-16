"""LATS Agent strategies for Math."""

import re

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from agential.cog.lats.functional import (
    _build_failed_trajectory_format,
    _build_reflection_format,
    _prompt_agent,
    _prompt_reflection,
    _prompt_value,
    get_node_trajectory_math,
    get_unique_trajectories,
    parse_math_action,
    parse_math_value,
)
from agential.cog.lats.node import Node
from agential.cog.lats.output import LATSReActStepOutput, LATSSimulationOutput
from agential.cog.lats.strategies.base import LATSBaseStrategy
from agential.eval.em import EM
from agential.llm.llm import BaseLLM, ModelResponse
from agential.utils.general import get_token_cost_time, safe_execute
from agential.utils.parse import remove_newline


class LATSMathStrategy(LATSBaseStrategy):
    """A strategy class for Math benchmarks using the LATS agent.

    Attributes:
        llm: The language model to be used for generating responses.
        n_samples (int): Number of samples to generate, default is 5.
        max_reflections (int): Maximum number of reflections allowed, default is 4.
        depth_limit (int): Maximum depth of the search tree, default is 7.
        max_unique (int): Maximum number of unique samples to consider, default is 5.
        cache_values (bool): Whether to cache values, default is True.

    The strategy uses these parameters to fine-tune its behavior and performance
    in question-answering tasks.
    """
        
    def __init__(
        self,
        llm: BaseLLM,
        n_samples: int = 5,
        max_reflections: int = 4,
        depth_limit: int = 7,
        max_unique: int = 5,
        cache_values: bool = True,
        testing: bool = False,
    ) -> None:
        """Initialize."""
        super().__init__(
            llm=llm,
            n_samples=n_samples,
            max_reflections=max_reflections,
            depth_limit=depth_limit,
            max_unique=max_unique,
            cache_values=cache_values,
            testing=testing,
        )

        self.failed_trajectories: List[Dict[str, str]] = []
        self.reflection_map: List[Dict[str, str]] = []
        self.value_cache: Dict[str, str] = {}
        self.root: Optional[Node] = None

    def generate_children_nodes(
        self,
        node: Node,
        question: str,
        key: str,
        examples: str,
        reflect_examples: str,
        prompt: str,
        reflect_prompt: str,
        additional_keys: Dict[str, str],
        reflect_additional_keys: Dict[str, str],
    ) -> Tuple[List[Node], List[ModelResponse], List[ModelResponse]]:
        """Generate child nodes for the given node.

        Args:
            node (Node): The current node to expand.
            question (str): The main question or task.
            key (str): The answer key for evaluation.
            examples (str): Examples for context.
            reflect_examples (str): Examples for reflection.
            prompt (str): The prompt template for generation.
            reflect_prompt (str): The prompt template for reflection.
            additional_keys (Dict[str, str]): Additional keys for prompt formatting.
            reflect_additional_keys (Dict[str, str]): Additional keys for reflection prompt formatting.

        Returns:
            Tuple[List[Node], List[ModelResponse], List[ModelResponse]]: A list of generated child nodes, and the corresponding model responses.
        """
        reflections_str = ""
        if self.reflect_condition():
            reflections = self.reflect(
                question=question,
                examples=reflect_examples,
                prompt=reflect_prompt,
                additional_keys=reflect_additional_keys,
            )
            for reflection in reflections:
                reflections_str += (
                    _build_reflection_format(
                        trajectory=reflection["trajectory"],
                        reflection=reflection["reflection"],
                    )
                    + "\n\n"
                )

        trajectory = get_node_trajectory_math(node)

        unique_states = set()
        children_nodes, thought_model_responses, action_model_responses = [], [], []
        for _ in range(self.n_samples):
            trajectory_i, thought, thought_model_response = self.generate_thought(
                question=question,
                examples=examples,
                trajectory=trajectory,
                reflections=reflections_str,
                depth=node.depth,
                prompt=prompt,
                additional_keys=additional_keys,
            )
            trajectory_i, action_type, query, action_model_response = (
                self.generate_action(
                    question=question,
                    examples=examples,
                    trajectory=trajectory_i,
                    reflections=reflections_str,
                    depth=node.depth,
                    prompt=prompt,
                    additional_keys=additional_keys,
                )
            )

            unique_key = f"{thought}::{action_type}::{query}"
            if unique_key not in unique_states:
                unique_states.add(unique_key)

                _, reward, obs, done, external_tool_info = self.generate_observation(
                    key=key,
                    action_type=action_type,
                    query=query,
                    trajectory=trajectory_i,
                    depth=node.depth,
                )

                new_node = Node(
                    state=LATSReActStepOutput(
                        thought=thought,
                        action_type=action_type,
                        query=query,
                        observation=obs,
                        answer="" if not done else query,
                        external_tool_info=external_tool_info,
                    ),
                    parent=node,
                    depth=node.depth + 1,
                    is_terminal=reward == 1 or done,
                    reward=reward,
                )

                if new_node.is_terminal and reward == 0:
                    traversed_nodes = get_node_trajectory_math(new_node)
                    self.failed_trajectories.append(
                        {
                            "trajectory": traversed_nodes,
                            "final_answer": query,
                        }
                    )
            else:
                new_node = Node(
                    state=LATSReActStepOutput(
                        thought=thought,
                        action_type=action_type,
                        query=query,
                        observation="",
                        answer="",
                        external_tool_info={},
                    ),
                )

            thought_model_responses.append(thought_model_response)
            action_model_responses.append(action_model_response)
            children_nodes.append(new_node)

        return children_nodes, thought_model_responses, action_model_responses

    def generate_action(
        self,
        question: str,
        examples: str,
        trajectory: str,
        reflections: str,
        depth: int,
        prompt: str,
        additional_keys: Dict[str, str],
    ) -> Tuple[str, str, str, ModelResponse]:
        """Generate an action for the current step in the reasoning process.

        Args:
            question (str): The main question or task to be addressed.
            examples (str): Relevant examples to provide context for action generation.
            trajectory (str): The current trajectory or history of thoughts and actions.
            reflections (str): Previous reflections to guide the action generation.
            depth (int): The current depth in the search tree.
            prompt (str): The prompt template for action generation.
            additional_keys (Dict[str, str]): Additional keys for prompt formatting.

        Returns:
            Tuple[str, str, str, ModelResponse]: A tuple containing the updated trajectory, action type, query, and model response.
        """
        trajectory += f"\nAction {depth + 1}: "
        out = _prompt_agent(
            llm=self.llm,
            question=question,
            examples=examples,
            trajectory=trajectory,
            reflections=reflections,
            prompt=prompt,
            additional_keys=additional_keys,
        )
        action = out.choices[0].message.content

        action = action.split("Observation")[0].strip()
        action_type, query = parse_math_action(action)
        trajectory += f" {action_type}[\n```python\n{query}\n```\n]"

        return trajectory, action_type, query, out

    def generate_observation(
        self,
        key: str,
        action_type: str,
        query: str,
        trajectory: str,
        depth: int,
    ) -> Tuple[str, int, str, bool, Dict[str, Any]]:
        """Generate an observation based on the current action.

        Args:
            key (str): The answer key for evaluation.
            action_type (str): The type of action taken.
            query (str): The query associated with the action.
            trajectory (str): The current trajectory or history of thoughts and actions.
            depth (int): The current depth in the search tree.

        Returns:
            Tuple[str, int, str, bool, Dict[str, str]]: A tuple containing the updated trajectory,
            reward, observation, done flag, and external tool information.
        """
        external_tool_info = {"execution_status": "", "code_answer": ""}
        code_answer, execution_status = safe_execute(query)

        reward, done = 0, False
        trajectory += f"\nObservation {depth + 1}: "
        if action_type.lower() == "finish":
            external_tool_info["code_answer"] = code_answer[0]
            external_tool_info["execution_status"] = execution_status

            if EM(code_answer[0], key, normalize=False):
                obs = "Answer is CORRECT"
                reward = int(EM(code_answer[0], key, normalize=False))
            else:
                obs = "Answer is INCORRECT"
            done = True
        elif action_type.lower() == "calculate":
            external_tool_info["code_answer"] = code_answer[0]
            external_tool_info["execution_status"] = execution_status

            obs = f"\n```python\n{query}\n```\nExecution Status: {execution_status}\nOutput: answer = {code_answer[0]}"
        else:
            obs = (
                "Invalid Action. Valid Actions are Calculate[code] and Finish[answer]."
            )
        trajectory += obs

        return trajectory, reward, obs, done, external_tool_info

class LATSGSM8KStrategy(LATSMathStrategy):
    """A strategy class for the GSM8K benchmark using the LATS agent."""

    pass


class LATSSVAMPStrategy(LATSMathStrategy):
    """A strategy class for the SVAMP benchmark using the LATS agent."""

    pass


class LATSTabMWPStrategy(LATSMathStrategy):
    """A strategy class for the TabMWP benchmark using the LATS agent."""

    pass
