"""Functional module for Language Agent Tree Search (LATS)."""

from typing import Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages.human import HumanMessage
from langchain_core.prompts.prompt import PromptTemplate


def _build_reflection_prompt(
    question: str,
    examples: str,
    trajectory: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Constructs a reflection prompt for the Language Agent Tree Search (LATS) agent.

    Args:
        question (str): The main question or task for the agent to reflect on.
        examples (str): Relevant examples to provide context for the reflection.
        trajectory (str): The agent's current trajectory or thought process.
        prompt (str): The base prompt template to be formatted.
        additional_keys (Dict[str, str], optional): Additional key-value pairs for formatting the prompt. Defaults to {}.

    Returns:
        str: The fully formatted reflection prompt ready for use with the language model.
    """
    prompt = PromptTemplate.from_template(prompt).format(
        question=question, examples=examples, trajectory=trajectory, **additional_keys
    )
    return prompt


def _prompt_reflection(
    llm: BaseChatModel,
    question: str,
    examples: str,
    trajectory: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Generates a reflection using the language model based on the given inputs.

    Args:
        llm (BaseChatModel): The language model to use for generating the reflection.
        question (str): The main question or task.
        examples (str): Relevant examples to provide context.
        trajectory (str): The agent's current trajectory or thought process.
        prompt (str): The base prompt template to be used.
        additional_keys (Dict[str, str], optional): Additional formatting keys. Defaults to {}.

    Returns:
        str: The generated reflection content.
    """
    prompt = _build_reflection_prompt(
        question=question,
        examples=examples,
        trajectory=trajectory,
        prompt=prompt,
        additional_keys=additional_keys,
    )
    out = llm(
        [
            HumanMessage(
                content=prompt,
            )
        ]
    ).content
    assert isinstance(out, str)
    return out


def _build_value_prompt(
    question: str,
    examples: str,
    trajectory: str,
    failed_trajectories: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Constructs a value prompt for the LATS agent.

    Args:
        question (str): The main question or task.
        examples (str): Relevant examples to provide context.
        trajectory (str): The agent's current trajectory.
        failed_trajectories (str): Previously failed trajectories.
        prompt (str): The base prompt template to be formatted.
        additional_keys (Dict[str, str], optional): Additional formatting keys. Defaults to {}.

    Returns:
        str: The fully formatted value prompt.
    """
    prompt = PromptTemplate.from_template(prompt).format(
        question=question,
        examples=examples,
        trajectory=trajectory,
        failed_trajectories=failed_trajectories,
        **additional_keys,
    )
    return prompt


def _prompt_value(
    llm: BaseChatModel,
    question: str,
    examples: str,
    trajectory: str,
    failed_trajectories: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Generates a value assessment using the language model based on the given inputs.

    Args:
        llm (BaseChatModel): The language model to use for generating the value assessment.
        question (str): The main question or task.
        examples (str): Relevant examples to provide context.
        trajectory (str): The agent's current trajectory.
        failed_trajectories (str): Previously failed trajectories.
        prompt (str): The base prompt template to be used.
        additional_keys (Dict[str, str], optional): Additional formatting keys. Defaults to {}.

    Returns:
        str: The generated value assessment content.
    """
    prompt = _build_value_prompt(
        question=question,
        examples=examples,
        trajectory=trajectory,
        failed_trajectories=failed_trajectories,
        prompt=prompt,
        additional_keys=additional_keys,
    )
    out = llm(
        [
            HumanMessage(
                content=prompt,
            )
        ]
    ).content
    assert isinstance(out, str)
    return out


def _build_agent_prompt(
    question: str,
    examples: str,
    trajectory: str,
    reflections: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Constructs an agent prompt for the LATS agent.

    Args:
        question (str): The main question or task.
        examples (str): Relevant examples to provide context.
        trajectory (str): The agent's current trajectory.
        reflections (str): Previous reflections made by the agent.
        prompt (str): The base prompt template to be formatted.
        additional_keys (Dict[str, str], optional): Additional formatting keys. Defaults to {}.

    Returns:
        str: The fully formatted agent prompt.
    """
    prompt = PromptTemplate.from_template(prompt).format(
        question=question,
        examples=examples,
        trajectory=trajectory,
        reflections=reflections,
        **additional_keys,
    )
    return prompt


def _prompt_agent(
    llm: BaseChatModel,
    question: str,
    examples: str,
    trajectory: str,
    reflections: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Generates an agent response using the language model based on the given inputs.

    Args:
        llm (BaseChatModel): The language model to use for generating the agent response.
        question (str): The main question or task.
        examples (str): Relevant examples to provide context.
        trajectory (str): The agent's current trajectory.
        reflections (str): Previous reflections made by the agent.
        prompt (str): The base prompt template to be used.
        additional_keys (Dict[str, str], optional): Additional formatting keys. Defaults to {}.

    Returns:
        str: The generated agent response content.
    """
    prompt = _build_agent_prompt(
        question=question,
        examples=examples,
        trajectory=trajectory,
        reflections=reflections,
        prompt=prompt,
        additional_keys=additional_keys,
    )
    out = llm(
        [
            HumanMessage(
                content=prompt,
            )
        ]
    ).content
    assert isinstance(out, str)
    return out


def get_node_trajectory(node) -> str:
    """Generates a string representation of the trajectory from the given node to the root.

    Args:
        node: The current node in the tree.

    Returns:
        str: A string representation of the trajectory, including thoughts, actions, and observations.
    """
    trajectory = []

    while node:
        step = []
        if node.depth > 0:
            if node.state.get("thought"):
                step.append(f"Thought {node.depth}: {node.state['thought']}")
            if node.state.get("action"):
                step.append(f"Action {node.depth}: {node.state['action']}")
            if node.state.get("observation"):
                step.append(f"Observation {node.depth}: {node.state['observation']}")
            step = "\n".join(step)
        trajectory.append(step)
        node = node.parent

    return "\n".join(reversed(trajectory))


def get_unique_trajectories(failed_trajectories, max_unique) -> List[str]:
    """Extracts a specified number of unique trajectories from the given failed trajectories.

    Args:
        failed_trajectories (list): A list of dictionaries containing failed trajectories.
        max_unique (int, optional): The maximum number of unique trajectories to return.

    Returns:
        List[str]: A list of unique trajectory strings, up to the specified number.
    """
    unique_trajectories = []
    seen_final_answers = set()
    for traj in failed_trajectories:
        final_answer = traj.get("final_answer")
        if final_answer not in seen_final_answers:
            unique_trajectories.append(traj["trajectory"])
            seen_final_answers.add(final_answer)
        if len(unique_trajectories) >= max_unique:
            break
    return unique_trajectories
