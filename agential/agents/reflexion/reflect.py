"""Reflecting module for Reflexion."""

from typing import Dict, List, Optional, Tuple

from agential.agents.base.modules.reflect import BaseReflector
from agential.agents.reflexion.functional import (
    _format_last_attempt,
    _format_reflections,
    cot_reflect_last_attempt,
    cot_reflect_last_attempt_and_reflexion,
    cot_reflect_reflexion,
    react_reflect_last_attempt,
    react_reflect_last_attempt_and_reflexion,
    react_reflect_reflexion,
)
from agential.agents.reflexion.prompts import (
    REFLECTION_AFTER_LAST_TRIAL_HEADER,
)
from agential.core.llm import BaseLLM, Response


class ReflexionCoTReflector(BaseReflector):
    """ReflexionCoT module for reflecting.

    This class encapsulates the logic for reflecting on a given context, question, and scratchpad content using various
    strategies. It leverages a language model to generate reflections and maintains a list of these reflections.

    Attributes:
        llm (BaseLLM): A language model used for generating reflections.
        reflections (Optional[List[str]]): A list to store the generated reflections.
        reflections_str (Optional[str]): The reflections formatted into a string.
        max_reflections: (int): An int specifying the max number of reflections to use in a subsequent run. Defaults to 3.
    """

    def __init__(
        self,
        llm: BaseLLM,
        reflections: Optional[List[str]] = None,
        reflections_str: Optional[str] = None,
        max_reflections: int = 3,
    ) -> None:
        """Initialization."""
        super().__init__(llm=llm)
        self.llm = llm
        self.reflections = reflections if reflections else []
        self.reflections_str = reflections_str if reflections_str else ""
        self.max_reflections = max_reflections

    def reflect(
        self,
        reflect_strategy: str,
        question: str,
        examples: str,
        scratchpad: str,
        prompt: str,
        additional_keys: Dict[str, str] = {},
    ) -> Tuple[List[str], str, Optional[Response]]:
        """Wrapper around ReflexionCoT's `cot_reflect` method in functional.

        This method calls the appropriate reflection function based on the provided strategy, passing in the necessary
        parameters including the language model, context, question, and scratchpad. It then updates the internal
        reflections list with the newly generated reflections.

        Args:
            reflect_strategy (str): The reflection strategy to be used ('last_attempt', 'reflexion', or 'last_attempt_and_reflexion').
            question (str): The question being addressed.
            examples (str): Example inputs for the prompt template.
            scratchpad (str): The scratchpad content related to the question.
            prompt (str): Reflect prompt template string.
            additional_keys (Dict[str, str]): Additional keys to be passed to the prompt template.

        Returns:
            Tuple[List[str], str, Optional[Response]]: A tuple of the updated list of reflections based on the selected strategy and the formatted
                reflections.

        Raises:
            NotImplementedError: If an unknown reflection strategy is specified.
        """
        if reflect_strategy == "last_attempt":
            reflections, reflections_out = cot_reflect_last_attempt(scratchpad)
            reflections_str = _format_last_attempt(question, scratchpad)
        elif reflect_strategy == "reflexion":
            reflections, reflections_out = cot_reflect_reflexion(
                llm=self.llm,
                reflections=self.reflections,
                examples=examples,
                question=question,
                scratchpad=scratchpad,
                prompt=prompt,
                additional_keys=additional_keys,
            )
            reflections = reflections[-self.max_reflections :]
            reflections_str = _format_reflections(reflections)

        elif reflect_strategy == "last_attempt_and_reflexion":
            reflections, reflections_out = cot_reflect_last_attempt_and_reflexion(
                llm=self.llm,
                examples=examples,
                question=question,
                scratchpad=scratchpad,
                prompt=prompt,
                additional_keys=additional_keys,
            )
            reflections = reflections[-self.max_reflections :]
            reflections_str = _format_last_attempt(question, scratchpad)
            reflections_str += "\n" + _format_reflections(
                reflections, REFLECTION_AFTER_LAST_TRIAL_HEADER
            )
        else:
            raise NotImplementedError(
                f"Unknown reflection strategy: {reflect_strategy}."
            )

        self.reflections = reflections
        self.reflections_str = reflections_str

        return reflections, reflections_str, reflections_out

    def reset(self) -> None:
        """Resets the reflections and reflections_str."""
        self.reflections = []
        self.reflections_str = ""


class ReflexionReActReflector(BaseReflector):
    """ReflexionReAct module for reflecting.

    This class encapsulates the logic for reflecting on a given context, question, and scratchpad content using various
    strategies. It leverages a language model to generate reflections and maintains a list of these reflections.

    Attributes:
        llm (BaseLLM): A language model used for generating reflections.
        reflections (Optional[List[str]]): A list to store the generated reflections.
        reflections_str (Optional[str]): The reflections formatted into a string.
        max_reflections: (int): An int specifying the max number of reflections to use in a subsequent run. Defaults to 3.
    """

    def __init__(
        self,
        llm: BaseLLM,
        reflections: Optional[List[str]] = None,
        reflections_str: Optional[str] = None,
        max_reflections: int = 3,
    ) -> None:
        """Initialization."""
        super().__init__(llm=llm)
        self.llm = llm
        self.reflections = reflections if reflections else []
        self.reflections_str = reflections_str if reflections_str else ""
        self.max_reflections = max_reflections

    def reflect(
        self,
        reflect_strategy: str,
        question: str,
        examples: str,
        scratchpad: str,
        prompt: str,
        additional_keys: Dict[str, str] = {},
    ) -> Tuple[List[str], str, Optional[Response]]:
        """Wrapper around ReflexionReAct's `react_reflect` method in functional.

        This method calls the appropriate reflection function based on the provided strategy, passing in the necessary
        parameters including the language model, context, question, and scratchpad. It then updates the internal
        reflections list with the newly generated reflections.

        Args:
            reflect_strategy (str): The reflection strategy to be used ('last_attempt', 'reflexion', or 'last_attempt_and_reflexion').
            question (str): The question being addressed.
            examples (str): Example inputs for the prompt template.
            scratchpad (str): The scratchpad content related to the question.
            prompt (str, optional): Reflect prompt template string.
            additional_keys (Dict[str, str]): Additional keys. Defaults to {}.

        Returns:
            Tuple[List[str], str, Optional[Response]]: A tuple of the updated list of reflections based on the selected strategy and the formatted
                reflections.

        Raises:
            NotImplementedError: If an unknown reflection strategy is specified.
        """
        if reflect_strategy == "last_attempt":
            reflections, reflections_out = react_reflect_last_attempt(scratchpad)
            reflections_str = _format_last_attempt(question, scratchpad)
        elif reflect_strategy == "reflexion":
            reflections, reflections_out = react_reflect_reflexion(
                llm=self.llm,
                reflections=self.reflections,
                question=question,
                examples=examples,
                scratchpad=scratchpad,
                prompt=prompt,
                additional_keys=additional_keys,
            )
            reflections = reflections[-self.max_reflections :]
            reflections_str = _format_reflections(reflections)
        elif reflect_strategy == "last_attempt_and_reflexion":
            reflections, reflections_out = react_reflect_last_attempt_and_reflexion(
                llm=self.llm,
                question=question,
                examples=examples,
                scratchpad=scratchpad,
                prompt=prompt,
                additional_keys=additional_keys,
            )
            reflections = reflections[-self.max_reflections :]
            reflections_str = _format_last_attempt(question, scratchpad)
            reflections_str += "\n" + _format_reflections(
                reflections, REFLECTION_AFTER_LAST_TRIAL_HEADER
            )
        else:
            raise NotImplementedError(
                f"Unknown reflection strategy: {reflect_strategy}."
            )

        self.reflections = reflections
        self.reflections_str = reflections_str

        return reflections, reflections_str, reflections_out

    def reset(self) -> None:
        """Clears the reflections and reflections_str."""
        self.reflections = []
        self.reflections_str = ""
