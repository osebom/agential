"""Unit tests for Self-Refine code strategies."""

from agential.cog.fewshots.humaneval import HUMANEVAL_FEWSHOT_EXAMPLES_POT
from agential.cog.self_refine.prompts import (
    HUMANEVAL_CRITIQUE_FEWSHOT_EXAMPLES,
    SELF_REFINE_CRITIQUE_INSTRUCTION_HUMANEVAL,
    SELF_REFINE_INSTRUCTION_HUMANEVAL,
)
from agential.cog.self_refine.strategies.code import (
    SelfRefineCodeStrategy,
    SelfRefineHEvalStrategy,
    SelfRefineMBPPStrategy,
)
from agential.llm.llm import MockLLM


def test_init() -> None:
    """Test SelfRefinecodeStrategy initialization."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = SelfRefineCodeStrategy(llm=llm, patience=3)
    assert strategy.llm == llm
    assert strategy.patience == 3
    assert strategy._prev_code_answer == ""
    assert strategy.patience_counter == 0
    assert not strategy._halt
    assert strategy._prompt_metrics == {
        "answer": None,
        "critique": None,
        "updated_answer": None,
    }


def test_generate() -> None:
    """Tests SelfRefineCodeStrategy generate."""
    llm = MockLLM(
        "gpt-3.5-turbo",
        responses=[
            'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False\n'
        ],
    )

    strategy = SelfRefineCodeStrategy(llm=llm)

    question = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n'

    answer = strategy.generate(
        question=question,
        examples=HUMANEVAL_FEWSHOT_EXAMPLES_POT,
        prompt=SELF_REFINE_INSTRUCTION_HUMANEVAL,
        additional_keys={},
    )
    assert (
        answer
        == 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'
    )
    assert strategy._prompt_metrics == {
        "answer": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "prompt_tokens_cost": 1.5e-05,
            "completion_tokens_cost": 3.9999999999999996e-05,
            "total_tokens_cost": 5.4999999999999995e-05,
            "time_sec": 0.5,
        },
        "critique": None,
        "updated_answer": None,
    }


def test_generate_critique() -> None:
    """Tests SelfRefineCodeStrategy generate_critique."""
    gt_critique = "The function incorrectly returns True for a list without duplicates due to a logical error in the comparison operation. For example, with `names_list = ['Alice', 'Bob', 'Charlie', 'Dave']`, the function still returns True. The line `return len(names_list) != len(set(names_list)) - 1` checks for duplicates by comparing the list's length with the set's length (which removes duplicates), subtracting one to allow exactly one duplicate. However, this logic is flawed. The subtraction causes a false positive for duplicates when there is any unique item, as it misinterprets the size difference. The function thus fails due to a critical error in this comparison, leading to incorrect duplicate identification."
    responses = [
        "The function incorrectly returns True for a list without duplicates due to a logical error in the comparison operation. For example, with `names_list = ['Alice', 'Bob', 'Charlie', 'Dave']`, the function still returns True. The line `return len(names_list) != len(set(names_list)) - 1` checks for duplicates by comparing the list's length with the set's length (which removes duplicates), subtracting one to allow exactly one duplicate. However, this logic is flawed. The subtraction causes a false positive for duplicates when there is any unique item, as it misinterprets the size difference. The function thus fails due to a critical error in this comparison, leading to incorrect duplicate identification."
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    strategy = SelfRefineCodeStrategy(llm=llm)
    question = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n'
    answer = 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'
    tests = "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\n\ncheck(has_close_elements)"

    critique = strategy.generate_critique(
        question=question,
        examples=HUMANEVAL_CRITIQUE_FEWSHOT_EXAMPLES,
        answer=answer,
        prompt=SELF_REFINE_CRITIQUE_INSTRUCTION_HUMANEVAL,
        additional_keys={"tests": tests},
    )

    assert critique == gt_critique
    assert not strategy._halt
    assert strategy._prev_code_answer == answer
    assert strategy.patience_counter == 0
    assert strategy._prompt_metrics == {
        "answer": None,
        "critique": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "prompt_tokens_cost": 1.5e-05,
            "completion_tokens_cost": 3.9999999999999996e-05,
            "total_tokens_cost": 5.4999999999999995e-05,
            "time_sec": 0.5,
        },
        "updated_answer": None,
    }

    # Test early stopping.
    gt_critique = "The function incorrectly returns True for a list without duplicates due to a logical error in the comparison operation. For example, with `names_list = ['Alice', 'Bob', 'Charlie', 'Dave']`, the function still returns True. The line `return len(names_list) != len(set(names_list)) - 1` checks for duplicates by comparing the list's length with the set's length (which removes duplicates), subtracting one to allow exactly one duplicate. However, this logic is flawed. The subtraction causes a false positive for duplicates when there is any unique item, as it misinterprets the size difference. The function thus fails due to a critical error in this comparison, leading to incorrect duplicate identification."
    responses = [
        "The function incorrectly returns True for a list without duplicates due to a logical error in the comparison operation. For example, with `names_list = ['Alice', 'Bob', 'Charlie', 'Dave']`, the function still returns True. The line `return len(names_list) != len(set(names_list)) - 1` checks for duplicates by comparing the list's length with the set's length (which removes duplicates), subtracting one to allow exactly one duplicate. However, this logic is flawed. The subtraction causes a false positive for duplicates when there is any unique item, as it misinterprets the size difference. The function thus fails due to a critical error in this comparison, leading to incorrect duplicate identification."
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)

    question = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n'
    answer = 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'
    tests = "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\n\ncheck(has_close_elements)"
    strategy = SelfRefineCodeStrategy(llm=llm, patience=1)
    strategy._prev_code_answer = 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'

    critique = strategy.generate_critique(
        question=question,
        examples=HUMANEVAL_CRITIQUE_FEWSHOT_EXAMPLES,
        answer=answer,
        prompt=SELF_REFINE_CRITIQUE_INSTRUCTION_HUMANEVAL,
        additional_keys={"tests": tests},
    )
    assert critique == gt_critique
    assert strategy.patience_counter == 1
    assert strategy._halt is True
    assert (
        strategy._prev_code_answer
        == 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'
    )
    assert strategy._prompt_metrics == {
        "answer": None,
        "critique": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "prompt_tokens_cost": 1.5e-05,
            "completion_tokens_cost": 3.9999999999999996e-05,
            "total_tokens_cost": 5.4999999999999995e-05,
            "time_sec": 0.5,
        },
        "updated_answer": None,
    }


def test_create_output_dict() -> None:
    """Tests SelfRefineCodeStrategy create_output_dict."""
    strategy = SelfRefineCodeStrategy(llm=MockLLM("gpt-3.5-turbo", responses=[]))
    answer = 'from typing import List\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    """\n    for i in range(len(numbers) - 1):\n        if abs(numbers[i] - numbers[i + 1]) < threshold:\n            return True\n    return False'
    critique = "Critique: Your solution is incorrect."
    output_dict = strategy.create_output_dict(answer, critique)
    assert output_dict == {
        "answer": answer,
        "critique": critique,
        "prompt_metrics": {"answer": None, "critique": None, "updated_answer": None},
    }


def test_update_answer_based_on_critique() -> None:
    """Tests SelfRefineCodeStrategy update_answer_based_on_critique."""
    gt_answer = 'from typing import List\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n    for i in range(len(numbers)):\n        for j in range(i + 1, len(numbers)):\n            if abs(numbers[i] - numbers[j]) < threshold:\n                return True\n    return False'
    responses = [
        '```python\nfrom typing import List\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n    for i in range(len(numbers)):\n        for j in range(i + 1, len(numbers)):\n            if abs(numbers[i] - numbers[j]) < threshold:\n                return True\n    return False\n```'
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    strategy = SelfRefineCodeStrategy(llm=llm, patience=2)
    new_answer = strategy.update_answer_based_on_critique(
        question="", examples="", answer="", critique="", prompt="", additional_keys={}
    )
    assert new_answer == gt_answer
    assert strategy._prompt_metrics == {
        "answer": None,
        "critique": None,
        "updated_answer": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "prompt_tokens_cost": 1.5e-05,
            "completion_tokens_cost": 3.9999999999999996e-05,
            "total_tokens_cost": 5.4999999999999995e-05,
            "time_sec": 0.5,
        },
    }


def test_halting_condition() -> None:
    """Tests SelfRefineCodeStrategy halting_condition."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = SelfRefineCodeStrategy(llm=llm, patience=2)

    # Initially, halting condition should be False.
    assert strategy.halting_condition() is False

    # Simulate the halting condition being met.
    strategy._halt = True
    assert strategy.halting_condition() is True


def test_reset() -> None:
    """Tests SelfRefineCodeStrategy reset."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = SelfRefineCodeStrategy(llm=llm, patience=2)

    strategy._prev_code_answer = "result = 42"
    strategy.patience_counter = 1
    strategy._halt = True
    strategy.reset()
    assert strategy._prev_code_answer == ""
    assert strategy.patience_counter == 0
    assert not strategy._halt
    assert strategy._prompt_metrics == {
        "answer": None,
        "critique": None,
        "updated_answer": None,
    }


def test_instantiate_strategies() -> None:
    """Test instantiate all Code strategies."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    assert isinstance(SelfRefineHEvalStrategy(llm=llm), SelfRefineHEvalStrategy)
    assert isinstance(SelfRefineMBPPStrategy(llm=llm), SelfRefineMBPPStrategy)
