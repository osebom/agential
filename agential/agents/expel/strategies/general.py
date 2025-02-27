"""ExpeL Agent strategies for QA."""

import time

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from agential.agents.expel.functional import (
    _prompt_all_success_critique,
    _prompt_compare_critique,
    accumulate_metrics,
    categorize_experiences,
    gather_experience,
    get_folds,
    parse_insights,
    remove_err_operations,
    retrieve_insight_index,
)
from agential.agents.expel.memory import (
    ExpeLExperienceMemory,
    ExpeLInsightMemory,
)
from agential.agents.expel.output import ExpeLGenerateOutput, ExpeLOutput
from agential.agents.expel.strategies.base import ExpeLBaseStrategy
from agential.agents.reflexion.agent import ReflexionReAct
from agential.core.llm import BaseLLM, Response
from agential.utils.general import shuffle_chunk_list


class ExpeLGeneralStrategy(ExpeLBaseStrategy):
    """A general strategy class for the ExpeL agent.

    Attributes:
        llm (BaseLLM): The language model used for generating answers and critiques.
        reflexion_react_agent (ReflexionReAct): The ReflexionReAct agent.
        experience_memory (ExpeLExperienceMemory): Memory module for storing experiences. Default is None.
        insight_memory (ExpeLInsightMemory): Memory module for storing insights derived from experiences. Default is None.
        success_batch_size (int): Batch size for processing success experiences in generating insights. Default is 8.
        extract_init_insights (bool): Whether to extract initial insights from experiences. Default is True.
        testing (bool): Whether to run in testing mode. Defaults to False.
    """

    def __init__(
        self,
        llm: BaseLLM,
        reflexion_react_agent: ReflexionReAct,
        experience_memory: Optional[ExpeLExperienceMemory] = None,
        insight_memory: Optional[ExpeLInsightMemory] = None,
        success_batch_size: int = 8,
        extract_init_insights: bool = True,
        testing: bool = False,
    ) -> None:
        """Initialization."""
        experience_memory = experience_memory or ExpeLExperienceMemory()
        insight_memory = insight_memory or ExpeLInsightMemory()

        self.extract_init_insights = (
            extract_init_insights and experience_memory.experiences != []
        )
        super().__init__(
            llm=llm,
            reflexion_react_agent=reflexion_react_agent,
            experience_memory=experience_memory,
            insight_memory=insight_memory,
            success_batch_size=success_batch_size,
            testing=testing,
        )

    def generate(
        self,
        question: str,
        key: str,
        examples: str,
        prompt: str,
        reflect_examples: str,
        reflect_prompt: str,
        reflect_strategy: str,
        additional_keys: Dict[str, str],
        reflect_additional_keys: Dict[str, str],
        use_dynamic_examples: bool,
        extract_insights: bool,
        patience: int,
        k_docs: int,
        num_fewshots: int,
        max_fewshot_tokens: int,
        reranker_strategy: Optional[str],
        reset: bool,
    ) -> ExpeLOutput:
        """Collects and stores experiences from interactions based on specified questions and strategies.

        This method invokes the ReflexionReAct agent to process a set of questions with corresponding keys,
        using the provided strategy, prompts, and examples. It captures the trajectories of the agent's reasoning
        and reflection process, storing them for future analysis and insight extraction.

        Parameters:
            questions (List[str]): A list of questions for the agent to process.
            keys (List[str]): Corresponding keys to the questions, used for internal tracking and analysis.
            examples (str): Examples to provide context or guidance for the ReflexionReAct agent.
            prompt (str): The initial prompt or instruction to guide the ReflexionReAct agent's process.
            reflect_examples (str): Examples specifically for the reflection phase of processing.
            reflect_prompt (str): The prompt or instruction guiding the reflection process.
            reflect_strategy (Optional[str]): The strategy to use for processing questions.
            additional_keys (Dict[str, str]): The additional keys.
            reflect_additional_keys (Dict[str, str]): Additional keys for the reflection phase.
            use_dynamic_examples (bool): A boolean specifying whether or not to use dynamic examples from ExpeL's memory.
            extract_insights (bool): Whether to extract insights from the experiences.
            patience (int): The number of times to retry the agent's process if it fails.
            k_docs (int): The number of documents to retrieve for the fewshot.
            num_fewshots (int): The number of examples to use for the fewshot.
            max_fewshot_tokens (int): The maximum number of tokens to use for the fewshot.
            reranker_strategy (Optional[str]): The strategy to use for re-ranking the retrieved.
            reset (bool): Whether to reset the agent's state for a new problem-solving session.

        Returns:
            ExpeLOutput: The output of the ExpeL agent.
        """
        start = time.time()

        compares_response: List[List[Response]] = []
        successes_response: List[List[Response]] = []

        # If the agent starts with experience, extract insights from the experiences.
        if self.extract_init_insights:
            compare_response, success_response = self.extract_insights(
                self.experience_memory.experiences
            )
            compares_response.append(compare_response)
            successes_response.append(success_response)
            self.extract_init_insights = False

        if reset:
            self.reset()

        # User has ability to override examples.
        if use_dynamic_examples:
            examples, additional_keys = self.get_dynamic_examples(
                question=question,
                examples=examples,
                k_docs=k_docs,
                num_fewshots=num_fewshots,
                max_fewshot_tokens=max_fewshot_tokens,
                reranker_strategy=reranker_strategy,
                additional_keys=additional_keys,
            )
        else:
            additional_keys.update({"insights": ""})

        experience: List[Dict[str, Any]] = self.gather_experience(
            questions=[question],
            keys=[key],
            examples=examples,
            prompt=prompt,
            reflect_examples=reflect_examples,
            reflect_prompt=reflect_prompt,
            reflect_strategy=reflect_strategy,
            additional_keys=[additional_keys],
            reflect_additional_keys=[reflect_additional_keys],
            patience=patience,
        )  # A single experience.

        if extract_insights:
            compare_response, success_response = self.extract_insights(experience)
            compares_response.append(compare_response)
            successes_response.append(success_response)

        generate_out = ExpeLGenerateOutput(
            examples=examples,
            insights=additional_keys.get("insights", ""),
            experience={
                k: v for k, v in experience[0].items() if k not in ["question", "key"]
            },
            experience_memory=deepcopy(self.experience_memory.show_memories()),
            insight_memory=deepcopy(self.insight_memory.show_memories()),
            compares_response=compares_response if extract_insights else None,
            successes_response=successes_response if extract_insights else None,
        )

        total_time = time.time() - start
        total_metrics = accumulate_metrics(
            compares_response=compares_response,
            successes_response=successes_response,
            experiences=experience,
        )
        out = ExpeLOutput(
            answer=experience[0]["trajectory"].additional_info[-1].steps[-1].answer,
            total_prompt_tokens=total_metrics["total_prompt_tokens"],
            total_completion_tokens=total_metrics["total_completion_tokens"],
            total_tokens=total_metrics["total_tokens"],
            total_prompt_cost=total_metrics["total_prompt_cost"],
            total_completion_cost=total_metrics["total_completion_cost"],
            total_cost=total_metrics["total_cost"],
            total_prompt_time=total_metrics["total_prompt_time"],
            total_time=total_time if not self.testing else 0.5,
            additional_info=generate_out,
        )

        return out

    def get_dynamic_examples(
        self,
        question: str,
        examples: str,
        k_docs: int,
        num_fewshots: int,
        max_fewshot_tokens: int,
        reranker_strategy: Optional[str],
        additional_keys: Dict[str, Any],
    ) -> Tuple[str, Dict[str, str]]:
        """Dynamically loads relevant past successful trajectories as few-shot examples and insights from the experience and insight memories, and returns the updated examples and additional keys.

        Args:
            question (str): The question to use for loading the relevant past successful trajectories.
            examples (str): The examples to use as a fallback if no dynamic examples are found.
            k_docs (int): The number of relevant past successful trajectories to load.
            num_fewshots (int): The number of few-shot examples to include.
            max_fewshot_tokens (int): The maximum number of tokens to include in the few-shot examples.
            reranker_strategy (Optional[str]): The reranker strategy to use for loading the relevant past successful trajectories.
            additional_keys (Dict[str, Any]): Additional keys to update with the loaded insights.

        Returns:
            Tuple[str, Dict[str, str]]: The updated examples and additional keys.
        """
        additional_keys = additional_keys.copy()

        # Dynamically load in relevant past successful trajectories as fewshot examples.
        dynamic_examples = self.experience_memory.load_memories(
            query=question,
            k_docs=k_docs,
            num_fewshots=num_fewshots,
            max_fewshot_tokens=max_fewshot_tokens,
            reranker_strategy=reranker_strategy,
        )["fewshots"]
        examples = "\n\n---\n\n".join(
            dynamic_examples if dynamic_examples else [examples]  # type: ignore
        )

        # Dynamically load in all insights.
        insights = self.insight_memory.load_memories()["insights"]
        insights = "".join(
            [f"{i}. {insight['insight']}\n" for i, insight in enumerate(insights)]
        )
        additional_keys.update({"insights": insights})

        return examples, additional_keys

    def gather_experience(
        self,
        questions: List[str],
        keys: List[str],
        examples: str,
        prompt: str,
        reflect_examples: str,
        reflect_prompt: str,
        reflect_strategy: str,
        additional_keys: List[Dict[str, str]],
        reflect_additional_keys: List[Dict[str, str]],
        patience: int,
    ) -> List[Dict[str, Any]]:
        """Gathers experience data for the Reflexion React agent, including questions, keys, examples, prompts, and additional keys. The gathered experience is added to the experience memory and returned as a dictionary.

        Args:
            questions (List[str]): A list of questions to gather experience for.
            keys (List[str]): A list of keys to associate with the gathered experience.
            examples (str): The examples to use for the experience.
            prompt (str): The prompt to use for the experience.
            reflect_examples (str): The examples to use for the reflection experience.
            reflect_prompt (str): The prompt to use for the reflection experience.
            reflect_strategy (str): The reflection strategy to use.
            additional_keys (List[Dict[str, str]]): Additional keys to associate with the gathered experience.
            reflect_additional_keys (List[Dict[str, str]]): Additional keys to associate with the reflection experience.
            patience (int): The patience to use for the experience gathering.

        Returns:
            List[Dict[str, Any]]: A list of experience outputs.
        """
        experiences = gather_experience(
            reflexion_react_agent=self.reflexion_react_agent,
            questions=questions,
            keys=keys,
            examples=examples,
            prompt=prompt,
            reflect_examples=reflect_examples,
            reflect_prompt=reflect_prompt,
            reflect_strategy=reflect_strategy,
            additional_keys=additional_keys,
            reflect_additional_keys=reflect_additional_keys,
            patience=patience,
        )

        self.experience_memory.add_memories(
            questions=[exp["question"] for exp in experiences],
            keys=[exp["key"] for exp in experiences],
            trajectories=[exp["trajectory"] for exp in experiences],
            reflections=[exp["reflections"] for exp in experiences],
        )
        return experiences

    def extract_insights(
        self, experiences: List[Dict[str, Any]]
    ) -> Tuple[List[Response], List[Response]]:
        """Extracts insights from the provided experiences and updates the `InsightMemory` accordingly.

        This method is responsible for analyzing the successful and failed trials in the provided experiences, comparing them, and generating insights that are then stored in the `InsightMemory`. The insights are generated using the `get_operations_compare` and `get_operations_success` functions, and the `update_insights` method is used to apply the generated operations to the `InsightMemory`.
        The method first categorizes the experiences into "compare" and "success" categories, and then processes the experiences in batches. For the "compare" category, it compares the successful trial with all previous failed trials and generates insights using the `get_operations_compare` function. For the "success" category, it concatenates the successful trials and generates insights using the `get_operations_success` function.

        Args:
            experiences (List[Dict[str, Any]]): A dictionary containing the experiences to be processed, including questions, trajectories, and other relevant data.

        Return:
            List[Response]: A list of compare responses.
            List[Response]: A list of success responses.
        """
        # Extract insights.
        categories = categorize_experiences(experiences)
        folds = get_folds(categories, len(experiences))

        compares_response: List[Response] = []
        successes_response: List[Response] = []
        for train_idxs in folds.values():
            train_category_idxs = {
                category: list(set(train_idxs).intersection(set(category_idxs)))  # type: ignore
                for category, category_idxs in categories.items()
            }

            # Compare.
            for train_idx in train_category_idxs["compare"]:
                question = experiences[train_idx]["question"]
                trajectory = experiences[train_idx]["trajectory"]

                # Compare the successful trial with all previous failed trials.
                success_trial = "".join(
                    f"Thought: {step.thought}\nAction: {step.action_type}[{step.query}]\nObservation: {step.observation}\n"
                    for step in trajectory.additional_info[-1].steps
                )
                for failed_trial in trajectory.additional_info[:-1]:
                    failed_trial = "".join(
                        f"Thought: {step.thought}\nAction: {step.action_type}[{step.query}]\nObservation: {step.observation}\n"
                        for step in failed_trial.steps
                    )
                    insights = self.insight_memory.load_memories()["insights"]

                    compare_out = _prompt_compare_critique(
                        llm=self.llm,
                        insights=insights,
                        question=question,
                        success_trial=success_trial,
                        failed_trial=failed_trial,
                        is_full=self.insight_memory.max_num_insights < len(insights),
                    )
                    compares_response.append(compare_out)
                    insights_str = compare_out.output_text
                    insights_str = insights_str.strip("\n").strip()

                    # Parse.
                    operations = parse_insights(insights_str)

                    # Remove no-ops.
                    operations = remove_err_operations(insights, operations)

                    self.update_insights(operations=operations)

            # Success.
            if train_category_idxs["success"]:
                batched_success_trajs_idxs = shuffle_chunk_list(
                    train_category_idxs["success"], self.success_batch_size
                )
                for success_idxs in batched_success_trajs_idxs:
                    insights = self.insight_memory.load_memories()["insights"]

                    # Concatenate batched successful trajectories.
                    concat_success_trajs = [
                        f"{experiences[idx]['question']}\n"
                        + "".join(
                            f"Thought: {step.thought}\nAction: {step.action_type}[{step.query}]\nObservation: {step.observation}\n"
                            for step in experiences[idx]["trajectory"]
                            .additional_info[0]
                            .steps
                        )
                        for idx in success_idxs
                    ]

                    success_trials = "\n\n".join(concat_success_trajs)

                    # Prompt.
                    success_out = _prompt_all_success_critique(
                        llm=self.llm,
                        insights=insights,
                        success_trajs_str=success_trials,
                        is_full=self.insight_memory.max_num_insights < len(insights),
                    )
                    successes_response.append(success_out)
                    insights_str = success_out.output_text
                    insights_str = insights_str.strip("\n").strip()

                    # Parse.
                    operations = parse_insights(insights_str)

                    # Remove no-ops.
                    operations = remove_err_operations(insights, operations)

                    self.update_insights(operations=operations)

        return compares_response, successes_response

    def update_insights(self, operations: List[Tuple[str, str]]) -> None:
        """Updates the insights in the `InsightMemory` based on the provided operations.

        The `operations` parameter is a list of tuples, where each tuple contains an operation type and an insight. The supported operation types are:
        - "REMOVE": Removes the insight from the `InsightMemory`.
        - "AGREE": Increases the score of the insight in the `InsightMemory`.
        - "EDIT": Updates the insight in the `InsightMemory` with the provided insight.
        - "ADD": Adds a new insight to the `InsightMemory` with a score of 2.

        This method is responsible for applying the various operations to the insights stored in the `InsightMemory`.

        Args:
            operations (List[Tuple[str, str]]): A list of tuples, where each tuple contains an operation type and an insight.
        """
        # Update rules with comparison insights.
        for i in range(len(operations)):
            insights = self.insight_memory.load_memories()["insights"]
            operation, operation_insight = operations[i]
            operation_type = operation.split(" ")[0]

            if operation_type == "REMOVE":
                insight_idx = retrieve_insight_index(insights, operation_insight)
                if insight_idx != -1:
                    self.insight_memory.delete_memories(insight_idx)
            elif operation_type == "AGREE":
                insight_idx = retrieve_insight_index(insights, operation_insight)
                if insight_idx != -1:
                    self.insight_memory.update_memories(
                        idx=insight_idx, update_type="AGREE"
                    )
            elif operation_type == "EDIT":
                insight_idx = int(operation.split(" ")[1])
                self.insight_memory.update_memories(
                    idx=insight_idx,
                    update_type="EDIT",
                    insight=operation_insight,
                )
            elif operation_type == "ADD":
                self.insight_memory.add_memories(
                    [{"insight": operation_insight, "score": 2}]
                )

    def reset(self) -> None:
        """Resets the ExperienceMemory and InsightMemory."""
        self.experience_memory.clear()
        self.insight_memory.clear()
