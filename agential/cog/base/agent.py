"""Base agent interface class."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from agential.cog.base.strategies import BaseStrategy


class BaseAgent(ABC):
    """Base agent class providing a general interface for agent operations."""

    @abstractmethod
    def get_fewshots(
        self, benchmark: str, fewshot_type: str, **kwargs: Any
    ) -> Dict[str, str]:
        """Retrieve few-shot examples based on the benchmark.

        Args:
            benchmark (str): The benchmark name.
            fewshot_type (str): The benchmark few-shot type.
            **kwargs (Any): Additional arguments.

        Returns:
            Dict[str, str]: A dictionary of few-shot examples.
        """
        pass

    @abstractmethod
    def get_prompts(self, benchmark: str, **kwargs: Any) -> Dict[str, str]:
        """Retrieve the prompt instructions based on the benchmark.

        Args:
            benchmark (str): The benchmark name.
            **kwargs (Any): Additional arguments.

        Returns:
            Dict[str, str]: A dictionary of prompt instructions.
        """
        pass

    @abstractmethod
    def get_strategy(self, benchmark: str, **kwargs: Any) -> BaseStrategy:
        """Returns an instance of the appropriate strategy based on the provided benchmark.

        Args:
            benchmark (str): The benchmark name.
            **kwargs (Dict[str, Any]): Additional keyword arguments to pass to
                the strategy's constructor.

        Returns:
            BaseStrategy: An instance of the appropriate strategy.
        """
        pass

    @abstractmethod
    def generate(self, *args: Any, **kwargs: Any) -> Any:
        """Generate a response."""
        raise NotImplementedError("Generate method not implemented.")

