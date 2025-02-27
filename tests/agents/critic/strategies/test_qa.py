"""Unit tests for CRITIC QA strategies."""

from unittest.mock import MagicMock

import pytest

from langchain_community.utilities.google_search import GoogleSearchAPIWrapper

from agential.agents.critic.output import CriticOutput, CriticStepOutput
from agential.agents.critic.prompts import (
    CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
    CRITIC_INSTRUCTION_HOTPOTQA,
    HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
)
from agential.agents.critic.strategies.qa import (
    CriticAmbigNQStrategy,
    CriticFEVERStrategy,
    CriticHotQAStrategy,
    CriticQAStrategy,
    CriticTriviaQAStrategy,
)
from agential.core.fewshots.hotpotqa import (
    HOTPOTQA_FEWSHOT_EXAMPLES_COT,
)
from agential.core.llm import BaseLLM, MockLLM, Response


def test_init() -> None:
    """Test CriticQAStrategy initialization."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    mock_search = MagicMock(spec=GoogleSearchAPIWrapper)
    strategy = CriticQAStrategy(llm=llm, search=mock_search)
    assert isinstance(strategy.llm, BaseLLM)
    assert isinstance(strategy.search, GoogleSearchAPIWrapper)
    assert strategy.evidence_length == 400
    assert strategy.num_results == 8
    assert strategy._query_history == []
    assert strategy._evidence_history == set()


def test_generate() -> None:
    """Tests CriticQAStrategy generate."""
    question = 'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring'

    gt_out = CriticOutput(
        answer="The kickboxer described in the question matches the profile of Badr Hari, a Dutch-Moroccan kickboxer who was once considered one of the best in the world. He has been involved in controversies related to his conduct in the sport, as well as crimes of violence outside of the ring",
        total_prompt_tokens=30,
        total_completion_tokens=60,
        total_tokens=90,
        total_prompt_cost=4.5e-05,
        total_completion_cost=0.00011999999999999999,
        total_cost=0.000165,
        total_prompt_time=1.5,
        total_time=0.5,
        additional_info=[
            CriticStepOutput(
                answer="The kickboxer described in the question matches the profile of Badr Hari, a Dutch-Moroccan kickboxer who was once considered one of the best in the world. He has been involved in controversies related to his conduct in the sport, as well as crimes of violence outside of the ring",
                critique="The kickboxer described in the question matches the profile of Badr Hari, a Dutch-Moroccan kickboxer who was once considered one of the best in the world. He has been involved in controversies related to his conduct in the sport, as well as crimes of violence outside of the ring",
                external_tool_info={"search_query": "", "search_result": ""},
                answer_response=[
                    Response(
                        input_text="",
                        output_text="Thought: Let's think step by step. The description matches that of kickboxer Badr Hari.\nAction: Finish[Badr Hari]",
                        prompt_tokens=10,
                        completion_tokens=20,
                        total_tokens=30,
                        prompt_cost=1.5e-05,
                        completion_cost=3.9999999999999996e-05,
                        total_cost=5.4999999999999995e-05,
                        prompt_time=0.5,
                    )
                ],
                critique_response=[
                    Response(
                        input_text="",
                        output_text="The answer provided is plausible as it matches the description given in the question.\n\n2. Truthfulness:\n\nLet's search the question in Google to verify the accuracy of the proposed answer:\nSearch Query: Who was once considered the best kick boxer in the world involved in controversies and crimes of violence outside of the ring?\nEvidence: Upon conducting a search, it is confirmed that Badr Hari, a Dutch-Moroccan kickboxer, fits the description provided in the question. He was once considered one of the best kickboxers globally but has been involved in controversies related to his behavior both in and out of the ring.\n\nThe proposed answer accurately identifies Badr Hari as the individual matching the description provided in the question.\n\nOverall, the proposed answer correctly identifies Badr Hari as the individual who was once considered the best kickboxer in the world but has been involved in controversies and crimes of violence. However, the explanation can be expanded to provide more context and clarity.",
                        prompt_tokens=10,
                        completion_tokens=20,
                        total_tokens=30,
                        prompt_cost=1.5e-05,
                        completion_cost=3.9999999999999996e-05,
                        total_cost=5.4999999999999995e-05,
                        prompt_time=0.5,
                    ),
                    Response(
                        input_text="",
                        output_text="the most possible answer: The kickboxer described in the question matches the profile of Badr Hari, a Dutch-Moroccan kickboxer who was once considered one of the best in the world. He has been involved in controversies related to his conduct in the sport, as well as crimes of violence outside of the ring.",
                        prompt_tokens=10,
                        completion_tokens=20,
                        total_tokens=30,
                        prompt_cost=1.5e-05,
                        completion_cost=3.9999999999999996e-05,
                        total_cost=5.4999999999999995e-05,
                        prompt_time=0.5,
                    ),
                ],
            )
        ],
    )
    responses = [
        "Thought: Let's think step by step. The description matches that of kickboxer Badr Hari.\nAction: Finish[Badr Hari]",
        "The answer provided is plausible as it matches the description given in the question.\n\n2. Truthfulness:\n\nLet's search the question in Google to verify the accuracy of the proposed answer:\nSearch Query: Who was once considered the best kick boxer in the world involved in controversies and crimes of violence outside of the ring?\nEvidence: Upon conducting a search, it is confirmed that Badr Hari, a Dutch-Moroccan kickboxer, fits the description provided in the question. He was once considered one of the best kickboxers globally but has been involved in controversies related to his behavior both in and out of the ring.\n\nThe proposed answer accurately identifies Badr Hari as the individual matching the description provided in the question.\n\nOverall, the proposed answer correctly identifies Badr Hari as the individual who was once considered the best kickboxer in the world but has been involved in controversies and crimes of violence. However, the explanation can be expanded to provide more context and clarity.",
        "the most possible answer: The kickboxer described in the question matches the profile of Badr Hari, a Dutch-Moroccan kickboxer who was once considered one of the best in the world. He has been involved in controversies related to his conduct in the sport, as well as crimes of violence outside of the ring.",
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    strategy = CriticQAStrategy(llm=llm, testing=True)
    out = strategy.generate(
        question=question,
        examples=HOTPOTQA_FEWSHOT_EXAMPLES_COT,
        critique_examples=HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
        prompt=CRITIC_INSTRUCTION_HOTPOTQA,
        critique_prompt=CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
        additional_keys={},
        critique_additional_keys={},
        max_interactions=3,
        use_tool=False,
        reset=True,
    )
    assert out == gt_out


def test_generate_answer() -> None:
    """Tests CriticQAStrategy generate_answer."""
    llm = MockLLM("gpt-3.5-turbo", responses=["Generated answer"])
    strategy = CriticQAStrategy(llm=llm)
    question = "What is the capital of France?"

    result, answer_response = strategy.generate_answer(
        question=question,
        examples=HOTPOTQA_FEWSHOT_EXAMPLES_COT,
        prompt=CRITIC_INSTRUCTION_HOTPOTQA,
        additional_keys={},
    )

    assert result == "Generated answer"
    assert answer_response == [
        Response(
            input_text="",
            output_text="Generated answer",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        )
    ]


def test_generate_critique() -> None:
    """Tests CriticQAStrategy generate_critique."""
    gt_result = '\n\nThe question asks for a detailed description of the individual, not just their name. The answer provided only mentions the name "Badr Hari" without any explanation or context. So, it\'s not plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring site: wikipedia.org\n> Evidence: [Badri Hari - Wikipedia] Badr Hari, is a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike\'s Gym in Oostzaan.\n\nThe evidence suggests that the person in question is indeed Badr Hari, as mentioned in the proposed answer.\n\nAbove all, the proposed answer correctly identifies Badr Hari as the individual in question, but lacks the detailed description required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring?\nHere\'s the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike\'s Gym in Oostzaan.'
    gt_search_query = 'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring site: wikipedia.org'
    gt_search_result = "[Badri Hari - Wikipedia] Badr Hari, is a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan.\n\nThe evidence suggests that the person in question is indeed Badr Hari, as mentioned in the proposed answer.\n\nAbove all, the proposed answer correctly identifies Badr Hari as the individual in question, but lacks the detailed description required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his \"unsportsmanlike conducts\" in the sport and crimes of violence outside of the ring?\nHere's the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan."
    gt_critique_response = [
        Response(
            input_text="",
            output_text='The question asks for a detailed description of the individual, not just their name. The answer provided only mentions the name "Badr Hari" without any explanation or context. So, it\'s not plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring site: wikipedia.org\n> Evidence: [Badr Hari - Wikipedia] Badr Hari is a Moroccan-Dutch super heavyweight kickboxer from the Netherlands, fighting out of Mike\'s Gym in Oostzaan.\n\nThe evidence confirms that Badr Hari fits the description provided in the question.\n\nThe proposed answer is correct in identifying Badr Hari as the individual described, but it lacks the detailed explanation required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring?\nHere\'s the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch super heavyweight kickboxer who has faced controversies for his unsportsmanlike behavior in the sport and involvement in violent crimes outside of the ring.',
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        ),
        Response(
            input_text="",
            output_text="[Badri Hari - Wikipedia] Badr Hari, is a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan.\n\nThe evidence suggests that the person in question is indeed Badr Hari, as mentioned in the proposed answer.\n\nAbove all, the proposed answer correctly identifies Badr Hari as the individual in question, but lacks the detailed description required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his \"unsportsmanlike conducts\" in the sport and crimes of violence outside of the ring?\nHere's the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan.",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        ),
    ]

    responses = [
        'The question asks for a detailed description of the individual, not just their name. The answer provided only mentions the name "Badr Hari" without any explanation or context. So, it\'s not plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring site: wikipedia.org\n> Evidence: [Badr Hari - Wikipedia] Badr Hari is a Moroccan-Dutch super heavyweight kickboxer from the Netherlands, fighting out of Mike\'s Gym in Oostzaan.\n\nThe evidence confirms that Badr Hari fits the description provided in the question.\n\nThe proposed answer is correct in identifying Badr Hari as the individual described, but it lacks the detailed explanation required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring?\nHere\'s the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch super heavyweight kickboxer who has faced controversies for his unsportsmanlike behavior in the sport and involvement in violent crimes outside of the ring.',
        "[Badri Hari - Wikipedia] Badr Hari, is a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan.\n\nThe evidence suggests that the person in question is indeed Badr Hari, as mentioned in the proposed answer.\n\nAbove all, the proposed answer correctly identifies Badr Hari as the individual in question, but lacks the detailed description required by the question.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his \"unsportsmanlike conducts\" in the sport and crimes of violence outside of the ring?\nHere's the most possible answer: The person in question is Badr Hari, a Moroccan-Dutch kickboxer from Amsterdam, Netherlands, fighting out of Mike's Gym in Oostzaan.",
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    strategy = CriticQAStrategy(llm=llm)
    question = 'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring'
    answer = "The person in question is Badr Hari."

    result, external_tool_info, finished, critique_response = (
        strategy.generate_critique(
            idx=0,
            question=question,
            examples=HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
            answer=answer,
            critique="",
            prompt=CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
            additional_keys={},
            use_tool=False,
            max_interactions=5,
        )
    )

    assert result == gt_result
    assert "search_query" in external_tool_info
    assert "search_result" in external_tool_info
    assert external_tool_info["search_query"] == gt_search_query
    assert external_tool_info["search_result"] == gt_search_result
    assert strategy._query_history == []
    assert strategy._evidence_history == set()
    assert not finished
    assert critique_response == gt_critique_response

    # Test with tool.
    gt_result = '\nThe question asks for a person known for controversies and crimes, and the answer "Badr Hari" is a person\'s name. So it\'s plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\n> Evidence: [agential-ai/agential: The encyclopedia of LLM-based agents - GitHub] \'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts"\xa0...\n\n'
    gt_search_query = 'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring'
    gt_title = "agential-ai/agential: The encyclopedia of LLM-based agents - GitHub"
    gt_link = "https://github.com/alckasoc/agential"
    gt_snippet = '\'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts"\xa0...'
    gt_query_history = [
        'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring'
    ]
    gt_evidence_history = set(
        {
            '\'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts"\xa0...'
        }
    )

    responses = [
        'The question asks for a person known for controversies and crimes, and the answer "Badr Hari" is a person\'s name. So it\'s plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\n> Evidence: [Badr Hari - Wikipedia] Badr Hari is a Moroccan-Dutch kickboxer from Amsterdam, fighting out of Mike\'s Gym in Oostzaan.\n\nThe evidence supports the answer that Badr Hari is known for controversies and crimes.\n\nTherefore, the proposed answer is plausible and truthful.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\nHere\'s the most possible answer: The person in question is Badr Hari.'
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    search_mock = MagicMock()
    search_mock.results.return_value = [
        {
            "title": "agential-ai/agential: The encyclopedia of LLM-based agents - GitHub",
            "link": "https://github.com/alckasoc/agential",
            "snippet": '\'Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts"\xa0...',
        }
    ]
    strategy = CriticQAStrategy(llm=llm, search=search_mock)

    gt_critique_response = [
        Response(
            input_text="",
            output_text='The question asks for a person known for controversies and crimes, and the answer "Badr Hari" is a person\'s name. So it\'s plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\n> Evidence: [Badr Hari - Wikipedia] Badr Hari is a Moroccan-Dutch kickboxer from Amsterdam, fighting out of Mike\'s Gym in Oostzaan.\n\nThe evidence supports the answer that Badr Hari is known for controversies and crimes.\n\nTherefore, the proposed answer is plausible and truthful.\n\nQuestion: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\nHere\'s the most possible answer: The person in question is Badr Hari.',
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        )
    ]
    result, external_tool_info, finished, critique_response = (
        strategy.generate_critique(
            idx=0,
            question=question,
            examples=HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
            answer=answer,
            critique="",
            prompt=CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
            additional_keys={},
            use_tool=True,
            max_interactions=5,
        )
    )

    assert result == gt_result
    assert "search_query" in external_tool_info
    assert "search_result" in external_tool_info
    assert external_tool_info["search_query"] == gt_search_query
    assert "title" in external_tool_info["search_result"]
    assert "link" in external_tool_info["search_result"]
    assert "snippet" in external_tool_info["search_result"]
    assert external_tool_info["search_result"]["title"] == gt_title
    assert external_tool_info["search_result"]["link"] == gt_link
    assert external_tool_info["search_result"]["snippet"] == gt_snippet
    assert strategy._query_history == gt_query_history
    assert strategy._evidence_history == gt_evidence_history
    assert not finished
    assert critique_response == gt_critique_response

    # Test most possible answer.
    gt_result = "Badr Hari"
    answer = "Let's think step by step. The kickboxer who fits this description is Badr Hari. So the answer is: Badr Hari."
    critique = '\n\nThe question asks for a kickboxer who was once considered the best in the world but has been involved in controversies and crimes. The answer "Badr Hari" fits this description, so it is plausible.\n\n2. Truthfulness:\n\nLet\'s search the question in google:\n\n> Search Query: Who was once considered the best kick boxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conducts" in the sport and crimes of violence outside of the ring\n> Evidence: [Controversies - Badr Hari - Wikipedia] Hari has been involved in a number of controversies relating to his "unsportsmanlike conduct" in the sport and crimes of violence outside of the ring.\n\nThe evidence confirms that Badr Hari fits the description provided in the question.\n\nOverall, the proposed answer is both plausible and truthful.\n\nQuestion: Who was once considered the best kickboxer in the world, however he has been involved in a number of controversies relating to his "unsportsmanlike conduct" in the sport and crimes of violence outside of the ring?\nHere\'s the most possible answer: Badr Hari.'
    responses = [
        'Thank you for the great question and proposed answer! The answer "Badr Hari" is both plausible and truthful based on the evidence found. Good job!',
        "the most possible answer: Badr Hari.",
    ]
    llm = MockLLM("gpt-3.5-turbo", responses=responses)
    strategy = CriticQAStrategy(llm=llm)

    gt_critique_response = [
        Response(
            input_text="",
            output_text='Thank you for the great question and proposed answer! The answer "Badr Hari" is both plausible and truthful based on the evidence found. Good job!',
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        ),
        Response(
            input_text="",
            output_text="the most possible answer: Badr Hari.",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            prompt_cost=1.5e-05,
            completion_cost=3.9999999999999996e-05,
            total_cost=5.4999999999999995e-05,
            prompt_time=0.5,
        ),
    ]
    result, external_tool_info, finished, critique_response = (
        strategy.generate_critique(
            idx=1,
            question=question,
            examples=HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
            answer=answer,
            critique=critique,
            prompt=CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
            additional_keys={},
            use_tool=False,
            max_interactions=3,
        )
    )

    assert result == gt_result
    assert external_tool_info == {"search_query": "", "search_result": ""}
    assert strategy._query_history == []
    assert strategy._evidence_history == set()
    assert finished
    assert critique_response == gt_critique_response


def test_create_output_dict() -> None:
    """Tests CriticQAStrategy create_output_dict."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = CriticQAStrategy(llm=llm)

    answer = "The capital of France is Paris."
    critique = "The answer is correct."
    external_tool_info = {"search_query": "capital of France", "search_result": "Paris"}

    result = strategy.create_output_dict(
        False, answer, critique, external_tool_info, [], []
    )
    assert result == {
        "answer": "The capital of France is Paris.",
        "critique": "The answer is correct.",
        "external_tool_info": {
            "search_query": "capital of France",
            "search_result": "Paris",
        },
        "critique_response": [],
        "answer_response": [],
    }

    result = strategy.create_output_dict(
        True, answer, critique, external_tool_info, [], []
    )
    assert result == {
        "answer": "The answer is correct.",
        "critique": "The answer is correct.",
        "external_tool_info": {
            "search_query": "capital of France",
            "search_result": "Paris",
        },
        "critique_response": [],
        "answer_response": [],
    }


def test_update_answer_based_on_critique() -> None:
    """Tests CriticQAStrategy update_answer_based_on_critique."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = CriticQAStrategy(llm=llm)
    question = "What is the capital of France?"
    answer = "The capital of France is Berlin."
    critique = "The answer is incorrect. The correct answer is Paris."

    result, answer_response = strategy.update_answer_based_on_critique(
        question=question,
        examples=HOTPOTQA_FEWSHOT_EXAMPLES_CRITIC,
        answer=answer,
        critique=critique,
        prompt=CRITIC_CRITIQUE_INSTRUCTION_HOTPOTQA,
        additional_keys={},
        external_tool_info={},
    )

    assert result == answer
    assert answer_response == []


def test_halting_condition() -> None:
    """Tests CriticQAStrategy halting_condition."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = CriticQAStrategy(llm=llm)

    result = strategy.halting_condition(True)

    assert result is True


def test_reset() -> None:
    """Tests CriticQAStrategy reset."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    strategy = CriticQAStrategy(llm=llm)
    strategy._query_history = ["query1"]
    strategy._evidence_history = {"evidence1"}

    strategy.reset()

    assert strategy._query_history == []
    assert strategy._evidence_history == set()


def test_handle_search_query() -> None:
    """Test CriticQAStrategy handle_search_query."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    mock_search = MagicMock(spec=GoogleSearchAPIWrapper)

    mock_search.results = MagicMock(
        return_value=[{"title": "Paris", "snippet": "The capital of France is Paris."}]
    )
    strategy = CriticQAStrategy(llm=llm, search=mock_search)

    idx = 0
    question = "What is the capital of France?"
    search_query = "capital of France"
    use_tool = True
    max_interactions = 5

    # Test when use_tool is False.
    search_result, context = strategy.handle_search_query(
        idx, question, search_query, False, max_interactions
    )

    assert search_result == {}
    assert context == "> Evidence: "

    # Test correctly throws error when search tool is used when not defined.
    with pytest.raises(ValueError):
        strategy = CriticQAStrategy(llm=llm)
        search_result, context = strategy.handle_search_query(
            idx,
            question,
            search_query,
            use_tool,
            max_interactions,
        )

    # Test valid search query.
    strategy = CriticQAStrategy(llm=llm, search=mock_search)
    search_result, context = strategy.handle_search_query(
        idx,
        question,
        search_query,
        use_tool,
        max_interactions,
    )

    assert search_result == {
        "title": "Paris",
        "snippet": "The capital of France is Paris.",
    }
    assert "> Evidence: [Paris] The capital of France is Paris." in context

    # Test correctly throws error when search tool is used when not defined.
    with pytest.raises(ValueError):
        strategy_without_search = CriticQAStrategy(llm=llm)
        strategy_without_search.handle_search_query(
            idx,
            question,
            search_query,
            use_tool,
            max_interactions,
        )

    # Test when search result has no snippet.
    mock_search.results = MagicMock(
        return_value=[{"title": "Paris", "link": "<a_link>", "snippet": "a snippet."}]
    )
    strategy = CriticQAStrategy(llm=llm, search=mock_search)
    search_result, context = strategy.handle_search_query(
        idx,
        question,
        search_query,
        use_tool,
        max_interactions,
    )

    assert search_result["title"] == "Paris"
    assert search_result["link"] == "<a_link>"
    assert search_result["snippet"] == "a snippet."
    assert context == "> Evidence: [Paris] a snippet.\n\n"

    # Test when search result snippet is already in evidence history.
    mock_search.results = MagicMock(
        return_value=[{"title": "Paris", "snippet": "The capital of France is Paris."}]
    )
    strategy._evidence_history.add("The capital of France is Paris.")
    search_result, context = strategy.handle_search_query(
        idx,
        question,
        search_query,
        use_tool,
        max_interactions,
    )

    assert search_result == {
        "title": "Paris",
        "snippet": "The capital of France is Paris.",
    }
    assert context == "> Evidence: [Paris] The capital of France is Paris.\n\n"

    # Test when num_results is exhausted.
    mock_search.results = MagicMock(
        return_value=[{"title": "Paris", "snippet": "The capital of France is Paris."}]
    )
    strategy._query_history = [search_query] * 3
    search_result, context = strategy.handle_search_query(
        idx,
        question,
        search_query,
        use_tool,
        max_interactions,
    )

    assert search_result == {
        "title": "Paris",
        "snippet": "The capital of France is Paris.",
    }
    assert context == "> Evidence: [Paris] The capital of France is Paris.\n\n"

    # Test when max_interactions is reached.
    idx = max_interactions - 2
    search_result, context = strategy.handle_search_query(
        idx,
        question,
        search_query,
        use_tool,
        max_interactions,
    )

    assert (
        "Let's give the most possible answer.\n\nQuestion: What is the capital of France?\nHere's "
        in context
    )


def test_instantiate_strategies() -> None:
    """Test instantiate all QA strategies."""
    llm = MockLLM("gpt-3.5-turbo", responses=[])
    hotqa_strategy = CriticHotQAStrategy(llm=llm)
    triviaqa_strategy = CriticTriviaQAStrategy(llm=llm)
    ambignq_strategy = CriticAmbigNQStrategy(llm=llm)
    fever_strategy = CriticFEVERStrategy(llm=llm)

    assert isinstance(hotqa_strategy, CriticHotQAStrategy)
    assert isinstance(triviaqa_strategy, CriticTriviaQAStrategy)
    assert isinstance(ambignq_strategy, CriticAmbigNQStrategy)
    assert isinstance(fever_strategy, CriticFEVERStrategy)
