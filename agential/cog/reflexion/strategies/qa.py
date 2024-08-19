"""Reflexion Agent strategies for QA."""

from typing import Any, Dict, List, Optional, Tuple

import tiktoken

from langchain_community.docstore.wikipedia import Wikipedia
from tiktoken import Encoding

from agential.cog.reflexion.functional import (
    _is_halted,
    _prompt_cot_agent,
    _prompt_react_agent,
    _truncate_scratchpad,
    parse_qa_action,
)
from agential.cog.reflexion.output import ReflexionReActStepOutput
from agential.cog.reflexion.reflect import (
    ReflexionCoTReflector,
    ReflexionReActReflector,
)
from agential.cog.reflexion.strategies.base import (
    ReflexionCoTBaseStrategy,
    ReflexionReActBaseStrategy,
)
from agential.cog.reflexion.strategies.general import ReflexionCoTGeneralStrategy
from agential.eval.em import EM
from agential.llm.llm import BaseLLM
from agential.utils.docstore import DocstoreExplorer
from agential.utils.metrics import PromptMetrics, get_token_cost_time
from agential.utils.parse import remove_newline


class ReflexionCoTQAStrategy(ReflexionCoTGeneralStrategy):
    """A strategy class for QA benchmarks using the ReflexionCoT agent.

    Attributes:
        llm (BaseLLM): The language model used for generating answers and critiques.
        reflector (Optional[ReflexionCoTReflector]): The reflector used for generating reflections. Defaults to None.
        max_reflections (int): The maximum number of reflections allowed. Defaults to 3.
        max_trials (int): The maximum number of trials allowed. Defaults to 3.
        testing (bool): Whether to run in testing mode. Defaults to False.
    """

    def __init__(
        self,
        llm: BaseLLM,
        reflector: Optional[ReflexionCoTReflector] = None,
        max_reflections: int = 3,
        max_trials: int = 3,
        testing: bool = False,
    ) -> None:
        """Initialization."""
        if reflector is None:
            reflector = ReflexionCoTReflector(llm=llm, max_reflections=max_reflections)
        super().__init__(
            llm=llm,
            reflector=reflector,
            max_reflections=max_reflections,
            max_trials=max_trials,
            testing=testing,
        )

    def generate_action(
        self,
        idx: int,
        scratchpad: str,
        question: str,
        examples: str,
        reflections: str,
        prompt: str,
        additional_keys: Dict[str, str],
    ) -> Tuple[str, str, str, PromptMetrics]:
        """Generates an action based on the question, examples, and prompt.

        Args:
            idx (int): The current index of the action.
            scratchpad (str): The current state of the scratchpad.
            question (str): The question to be answered.
            examples (str): Examples to guide the generation process.
            reflections (str): Reflections to consider during generation.
            prompt (str): The prompt used for generating the action.
            additional_keys (Dict[str, str]): Additional keys for the generation process.
            **kwargs (Any): Additional arguments.

        Returns:
            Tuple[str, str, str, PromptMetrics]: The updated scratchpad, the generated action, the action type, and the metrics for the action.
        """
        scratchpad += f"\nAction {idx}: "
        out = _prompt_cot_agent(
            llm=self.llm,
            examples=examples,
            reflections=reflections,
            question=question,
            scratchpad=scratchpad,
            prompt=prompt,
            additional_keys=additional_keys,
        )
        action = out.choices[0].message.content
        action = remove_newline(action).strip()
        scratchpad += action
        action_type, query = parse_qa_action(action)

        return scratchpad, action_type, query, get_token_cost_time(out)

    def generate_observation(
        self, idx: int, scratchpad: str, action_type: str, query: str, key: str
    ) -> Tuple[str, str, bool, str]:
        """Generates an observation based on the action type and query.

        Args:
            idx (int): The current index of the observation.
            scratchpad (str): The current state of the scratchpad.
            action_type (str): The type of action to be performed.
            query (str): The query for the action.
            key (str): The key for the observation.

        Returns:
            Tuple[str, str, bool, str, bool]: The updated scratchpad, the answer, a boolean indicating if the observation is correct, and the observation itself.
        """
        answer = ""
        scratchpad += f"\nObservation {idx}: "
        if action_type.lower() == "finish":
            answer = query
            if EM(answer, key):
                obs = "Answer is CORRECT"
            else:
                obs = "Answer is INCORRECT"
        else:
            obs = "Invalid action type, please try again."
        scratchpad += obs

        return scratchpad, answer, EM(answer, key), obs

    def halting_condition(
        self,
        idx: int,
        key: str,
        answer: str,
    ) -> bool:
        """Determines whether the halting condition has been met.

        Args:
            idx (int): The current step index.
            key (str): The key for the observation.
            answer (str): The answer generated.

        Returns:
            bool: True if the halting condition is met, False otherwise.
        """
        return EM(answer, key) or idx >= self.max_trials

    def reflect_condition(
        self,
        idx: int,
        reflect_strategy: Optional[str],
        key: str,
        answer: str,
    ) -> bool:
        """Determines whether the reflection condition has been met.

        Args:
            idx (int): The current step.
            reflect_strategy (Optional[str]): The strategy to use for reflection.
            key (str): The key for the observation.
            answer (str): The answer generated.

        Returns:
            bool: True if the reflection condition is met, False otherwise.
        """
        return idx > 0 and not EM(answer, key) and reflect_strategy is not None


class ReflexionReActQAStrategy(ReflexionReActBaseStrategy):
    """A strategy class for QA benchmarks using the ReflexionReAct agent.

    Attributes:
        llm (BaseLLM): The language model used for generating answers and critiques.
        reflector (Optional[ReflexionReActReflector]): The reflector used for generating reflections. Defaults to None.
        max_reflections (int): The maximum number of reflections allowed. Defaults to 3.
        max_trials (int): The maximum number of trials allowed. Defaults to 3.
        max_steps (int): The maximum number of steps allowed. Defaults to 6.
        max_tokens (int): The maximum number of tokens allowed. Defaults to 5000.
        enc (Encoding): The encoding for tokenization. Defaults to gpt-3.5-turbo.
        docstore (DocstoreExplorer): The document store explorer for retrieving relevant documents. Defaults to Wikipedia.
    """

    def __init__(
        self,
        llm: BaseLLM,
        reflector: Optional[ReflexionReActReflector] = None,
        max_reflections: int = 3,
        max_trials: int = 3,
        max_steps: int = 6,
        max_tokens: int = 5000,
        enc: Encoding = tiktoken.encoding_for_model("gpt-3.5-turbo"),
        docstore: DocstoreExplorer = DocstoreExplorer(Wikipedia()),
    ) -> None:
        """Initialization."""
        if reflector is None:
            reflector = ReflexionReActReflector(
                llm=llm, max_reflections=max_reflections
            )
        super().__init__(
            llm, reflector, max_reflections, max_trials, max_steps, max_tokens, enc
        )
        self.docstore = docstore

        self._finished = False
        self._answer = ""
        self._scratchpad = ""
        self._prompt_metrics: Dict[str, Any] = {"reflection": None}
        self._prompt_metrics_react: Dict[str, Any] = {"thought": None, "action": None}

    def generate(
        self,
        question: str,
        examples: str,
        reflections: str,
        prompt: str,
        additional_keys: Dict[str, str],
        **kwargs: Any,
    ) -> str:
        """Generates a thought based on the given question, examples, reflections, prompt, and additional keys.

        Args:
            question (str): The question to generate a thought for.
            examples (str): Examples to guide the thought generation process.
            reflections (str): Reflections to consider during the thought generation process.
            prompt (str): The prompt or instruction to guide the thought generation.
            additional_keys (Dict[str, str]): Additional keys for the thought generation process.
            kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            str: The generated thought.
        """
        max_steps = kwargs.get("max_steps", self.max_steps)  # type: ignore

        self._scratchpad += "\nThought:"
        out = _prompt_react_agent(
            llm=self.llm,
            question=question,
            examples=examples,
            reflections=reflections,
            scratchpad=self._scratchpad,
            max_steps=max_steps,  # type: ignore
            prompt=prompt,
            additional_keys=additional_keys,
        )
        self._prompt_metrics_react["thought"] = get_token_cost_time(out)
        thought = out.choices[0].message.content

        thought = remove_newline(thought).split("Action")[0].strip()
        self._scratchpad += " " + thought

        return thought

    def generate_action(
        self,
        question: str,
        examples: str,
        reflections: str,
        prompt: str,
        additional_keys: Dict[str, str],
        **kwargs: Any,
    ) -> Tuple[str, str]:
        """Generates an action based on the given question, examples, reflections, prompt, and additional keys.

        Args:
            question (str): The question to generate an action for.
            examples (str): Examples to guide the action generation process.
            reflections (str): Reflections to consider during the action generation process.
            prompt (str): The prompt or instruction to guide the action generation.
            additional_keys (Dict[str, str]): Additional keys for the action generation process.
            kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            Tuple[str, str]: The generated action type and query.
        """
        max_steps = kwargs.get("max_steps", self.max_steps)
        self._scratchpad += "\nAction:"
        out = _prompt_react_agent(
            llm=self.llm,
            question=question,
            examples=examples,
            reflections=reflections,
            scratchpad=self._scratchpad,
            max_steps=max_steps,  # type: ignore
            prompt=prompt,
            additional_keys=additional_keys,
        )
        self._prompt_metrics_react["action"] = get_token_cost_time(out)
        action = out.choices[0].message.content

        action = remove_newline(action).split("Observation")[0]
        self._scratchpad += " " + action
        action_type, query = parse_qa_action(action)

        return action_type, query

    def generate_observation(
        self,
        step_idx: int,
        action_type: str,
        query: str,
        key: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Generate an observation based on the action type and query.

        Args:
            step_idx (int): The index of the current step.
            action_type (str): The type of action to be performed.
            query (str): The query for the action.
            key (str): The key for the observation.

        Returns:
            Tuple[bool, str, Dict[str, Any]]: A tuple containing a boolean indicating whether the answer is correct, a string representing the observation,
                and a dictionary of the external tool outputs.
        """
        external_tool_info = {"search_result": "", "lookup_result": ""}

        self._scratchpad += f"\nObservation {step_idx}: "
        if action_type.lower() == "finish":
            self._answer = query
            self._finished = True
            if EM(self._answer, key):
                obs = "Answer is CORRECT"
            else:
                obs = "Answer is INCORRECT"
        elif action_type.lower() == "search":
            try:
                search_result = self.docstore.search(query)
                external_tool_info["search_result"] = search_result
                obs = remove_newline(search_result)
            except Exception:
                obs = "Could not find that page, please try again."
        elif action_type.lower() == "lookup":
            try:
                lookup_result = self.docstore.lookup(query)
                external_tool_info["lookup_result"] = lookup_result
                obs = remove_newline(lookup_result)
            except ValueError:
                obs = "The last page Searched was not found, so you cannot Lookup a keyword in it. Please try one of the similar pages given."
        else:
            obs = "Invalid Action. Valid Actions are Lookup[<topic>] Search[<topic>] and Finish[<answer>]."
        self._scratchpad += obs

        return EM(self._answer, key), obs, external_tool_info

    def create_output_dict(
        self,
        react_out: List[ReflexionReActStepOutput],
        reflections: List[str],
    ) -> Dict[str, Any]:
        """Create a dictionary containing the output of the ReflexionReAct agent.

        Args:
            react_out (List[ReflexionReActStepOutput]): The output of the ReflexionReAct agent, containing the thought, action type, query, observation, and whether the answer is correct for each step.
            reflections (List[str]): The reflections generated by the ReflexionReAct agent.

        Returns:
            Dict[str, str]: A dictionary containing the 'react_output' and 'reflections'.
        """
        return {
            "react_output": react_out,
            "reflections": reflections,
            "prompt_metrics": self._prompt_metrics,
        }

    def react_create_output_dict(
        self,
        thought: str,
        action_type: str,
        query: str,
        obs: str,
        external_tool_info: Dict[str, Any],
        is_correct: bool,
    ) -> Dict[str, Any]:
        """Create a dictionary containing the output of a single step in the ReflexionReAct agent.

        Args:
            thought (str): The thought generated in the current step.
            action_type (str): The type of action performed in the current step.
            query (str): The query or information related to the action performed in the current step.
            obs (str): The observation generated in the current step.
            external_tool_info (Dict[str, Any]): The external tool outputs.
            is_correct (bool): A boolean indicating whether the answer generated in the current step is correct.

        Returns:
            Dict[str, Any]: A dictionary containing the 'thought', 'action_type', 'query', 'observation', 'answer', 'external_tool_info', and 'is_correct' of the current step.
        """
        return {
            "thought": thought,
            "action_type": action_type,
            "query": query,
            "observation": obs,
            "answer": self._answer,
            "external_tool_info": external_tool_info,
            "is_correct": is_correct,
            "prompt_metrics": self._prompt_metrics_react,
        }

    def halting_condition(self, idx: int, key: str, **kwargs: Any) -> bool:
        """Determine whether the halting condition has been met.

        Args:
            idx (int): The current step index.
            key (str): The key for the observation.
            kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            bool: True if the halting condition is met, False otherwise. The halting condition is met when the answer is not correct and the current step index is less than the maximum number of trials plus one.
        """
        max_trials: int = kwargs.get("max_trials", self.max_trials)
        return EM(self._answer, key) or idx >= max_trials + 1

    def react_halting_condition(
        self,
        step_idx: int,
        question: str,
        examples: str,
        reflections: str,
        prompt: str,
        additional_keys: Dict[str, str],
        **kwargs: Any,
    ) -> bool:
        """Determine whether the halting condition has been met in the ReflexionReAct agent.

        Args:
            step_idx (int): The index of the current step.
            question (str): The question to generate an action for.
            examples (str): Examples to guide the action generation process.
            reflections (str): Reflections to consider during the action generation process.
            prompt (str): The prompt or instruction to guide the action generation.
            additional_keys (Dict[str, str]): Additional keys for the action generation process.
            kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            bool: True if the halting condition is met, False otherwise. The halting condition is met when the answer is not correct and the current step index is less than the maximum number of steps plus one.
        """
        max_steps = kwargs.get("max_steps", self.max_steps)

        return _is_halted(
            finished=self._finished,
            step_idx=step_idx,
            question=question,
            scratchpad=self._scratchpad,
            examples=examples,
            reflections=reflections,
            max_steps=max_steps,
            max_tokens=self.max_tokens,
            enc=self.enc,
            prompt=prompt,
            additional_keys=additional_keys,
        )

    def reset(self, **kwargs: Any) -> None:
        """Resets the internal state of the strategy.

        Resets the scratchpad and the finished flag.
        Resets only the scratchpad if specified with 'only_scratchpad'.

        Args:
            **kwargs (Any): Additional keyword arguments.
        """
        no_reflector = kwargs.get("no_reflector", False)
        if not no_reflector:
            self.reflector.reset()
        self._scratchpad = ""
        self._finished = False
        self._answer = ""
        self._prompt_metrics_react = {"thought": None, "action": None}
        self._prompt_metrics = {"reflection": None}

    def reflect(
        self,
        reflect_strategy: str,
        question: str,
        examples: str,
        prompt: str,
        additional_keys: Dict[str, str],
    ) -> Tuple[List[str], str]:
        """Reflects on a given question, context, examples, prompt, and additional keys using the specified reflection strategy.

        Args:
            reflect_strategy (str): The strategy to use for reflection.
            question (str): The question to be reflected upon.
            examples (str): Examples to guide the reflection process.
            prompt (str): The prompt or instruction to guide the reflection.
            additional_keys (Dict[str, str]): Additional keys for the reflection process.

        Returns:
            Tuple[List[str], str]: The reflections and reflection string.
        """
        reflections, reflections_str, reflections_out = self.reflector.reflect(
            reflect_strategy=reflect_strategy,
            question=question,
            examples=examples,
            scratchpad=_truncate_scratchpad(
                scratchpad=self._scratchpad, tokenizer=self.enc
            ),
            prompt=prompt,
            additional_keys=additional_keys,
        )
        self._prompt_metrics["reflection"] = (
            get_token_cost_time(reflections_out) if reflections_out else None
        )

        return reflections, reflections_str

    def reflect_condition(
        self,
        step_idx: int,
        reflect_strategy: Optional[str],
        question: str,
        examples: str,
        key: str,
        prompt: str,
        additional_keys: Dict[str, str],
        **kwargs: Dict[str, str],
    ) -> bool:
        """Determine whether the reflection condition has been met in the ReflexionReAct agent.

        Args:
            step_idx (int): The index of the current step.
            reflect_strategy (Optional[str]): The strategy to use for reflection.
            question (str): The question to be reflected upon.
            examples (str): Examples to guide the reflection process.
            key (str): The key for the observation.
            prompt (str): The prompt or instruction to guide the reflection.
            additional_keys (Dict[str, str]): Additional keys for the reflection process.
            kwargs (Dict[str, str]): Additional keyword arguments.

        Returns:
            bool: True if the reflection condition is met, False otherwise. The reflection condition is met when the agent is halted, the answer is not correct, and the reflection strategy is provided.
        """
        max_steps = kwargs.get("max_steps", self.max_steps)

        halted = _is_halted(
            finished=self._finished,
            step_idx=step_idx,
            question=question,
            scratchpad=self._scratchpad,
            examples=examples,
            reflections=self.reflector.reflections_str,
            max_steps=max_steps,  # type: ignore
            max_tokens=self.max_tokens,
            enc=self.enc,
            prompt=prompt,
            additional_keys=additional_keys,
        )

        return halted and not EM(self._answer, key) and reflect_strategy is not None


class ReflexionCoTHotQAStrategy(ReflexionCoTQAStrategy):
    """A strategy class for the HotpotQA benchmark using the ReflexionCoT agent."""

    pass


class ReflexionCoTTriviaQAStrategy(ReflexionCoTQAStrategy):
    """A strategy class for the TriviaQA benchmark using the ReflexionCoT agent."""

    pass


class ReflexionCoTAmbigNQStrategy(ReflexionCoTQAStrategy):
    """A strategy class for the AmbigNQ benchmark using the ReflexionCoT agent."""

    pass


class ReflexionCoTFEVERStrategy(ReflexionCoTQAStrategy):
    """A strategy class for the FEVER benchmark using the ReflexionCoT agent."""

    pass


class ReflexionReActHotQAStrategy(ReflexionReActQAStrategy):
    """A strategy class for the HotpotQA benchmark using the ReflexionReAct agent."""

    pass


class ReflexionReActTriviaQAStrategy(ReflexionReActQAStrategy):
    """A strategy class for the TriviaQA benchmark using the ReflexionReAct agent."""

    pass


class ReflexionReActAmbigNQStrategy(ReflexionReActQAStrategy):
    """A strategy class for the AmbigNQ benchmark using the ReflexionReAct agent."""

    pass


class ReflexionReActFEVERStrategy(ReflexionReActQAStrategy):
    """A strategy class for the FEVER benchmark using the ReflexionReAct agent."""

    pass
