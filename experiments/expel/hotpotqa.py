"""Run ExpeL on HotpotQA."""

import os
import warnings
import pickle

import tiktoken

warnings.filterwarnings('ignore')

from agential.agents.expel.agent import ExpeL
from agential.agents.expel.memory import ExpeLExperienceMemory, ExpeLInsightMemory
from agential.agents.reflexion.agent import ReflexionReAct
from agential.core.llm import LLM
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

import wandb
wandb.login()
from datasets import load_dataset

from experiments.utils import set_seed

import argparse

parser = argparse.ArgumentParser(description="Run Standard experiments.")
parser.add_argument("--model", type=str, default="gpt-3.5-turbo", help="The model")
parser.add_argument("--eval_model", type=str, default="gpt-4o", help="The evaluator model")
parser.add_argument("--seed", type=int, default=42, help="Random seed")
parser.add_argument("--max_reflections", type=int, default=3, help="Max reflections")
parser.add_argument("--max_trials", type=int, default=3, help="Max trials")
parser.add_argument("--max_steps", type=int, default=6, help="Max steps")
parser.add_argument("--max_tokens", type=int, default=5000, help="Max tokens")
parser.add_argument("--experience_memory_strategy", type=str, default="task", help="Experience memory strategy")
parser.add_argument("--embedder", type=str, default="huggingface", help="Embedder")
parser.add_argument("--experiences_path", type=str, default="", help="Experiences path (pkl)")
parser.add_argument("--max_insights", type=int, default=20, help="Max number of insights")
parser.add_argument("--leeway", type=int, default=5, help="Leeway")
parser.add_argument("--success_batch_size", type=int, default=8, help="Success batch size")
parser.add_argument("--patience", type=int, default=3, help="Patience")
parser.add_argument("--reflect_strategy", type=str, default="reflexion", help="Reflection strategy")
parser.add_argument("--use_dynamic_examples", type=bool, default=True, help="Boolean to use dynamic examples")
parser.add_argument("--extract_insights", type=bool, default=True, help="Boolean to extract insights")
parser.add_argument("--k_docs", type=int, default=24, help="Number of docs to retrieve")
parser.add_argument("--num_fewshots", type=int, default=6, help="Number of fewshots")
parser.add_argument("--max_fewshot_tokens", type=int, default=1500, help="Max tokens for fewshots")
parser.add_argument("--reranker_strategy", type=str, default="none", help="Reranker strategy")
args = parser.parse_args()

set_seed(args.seed)
root_dir = "output"
method_name = "expel"
benchmark = "hotpotqa"

if __name__ == '__main__':
    data = load_dataset("alckasoc/hotpotqa_500")['train']

    model = args.model
    eval_model = args.eval_model
    seed = args.seed
    max_reflections = args.max_reflections
    max_trials = args.max_trials
    max_steps = args.max_steps
    max_tokens = args.max_tokens
    experience_memory_strategy = args.experience_memory_strategy
    embedder = args.embedder
    experiences_path = args.experiences_path
    max_insights = args.max_insights
    leeway = args.leeway
    success_batch_size = args.success_batch_size
    patience = args.patience
    reflect_strategy = args.reflect_strategy
    use_dynamic_examples = args.use_dynamic_examples
    extract_insights = args.extract_insights
    k_docs = args.k_docs
    num_fewshots = args.num_fewshots
    max_fewshot_tokens = args.max_fewshot_tokens
    reranker_strategy = args.reranker_strategy if args.reranker_strategy != "none" else None

    if experiences_path:
        with open(experiences_path, 'rb') as f:
            experiences = pickle.load(f)
    else:
        experiences = []

    embedder_dict = {
        "huggingface": HuggingFaceEmbeddings
    }

    output_path = os.path.join(root_dir, benchmark)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    llm = LLM(
        model, 
        organization=os.getenv("OPENAI_ORGANIZATION"), 
        temperature=0,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        seed=seed
    )

    eval_llm = LLM(
        eval_model,
        organization=os.getenv("OPENAI_ORGANIZATION"),
        temperature=0,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        seed=seed
    )

    try:
        enc = tiktoken.encoding_for_model(args.model)
    except:
        enc = tiktoken.get_encoding("gpt-3.5-turbo")

    reflexion_react_agent = ReflexionReAct(
        llm=llm,
        benchmark=benchmark,
        max_reflections=max_reflections,
        max_trials=max_trials,
        max_steps=max_steps,
        max_tokens=max_tokens,
        enc=enc,
    )

    agent = ExpeL(
        llm=llm,
        benchmark=benchmark,
        reflexion_react_agent=reflexion_react_agent,
        experience_memory=ExpeLExperienceMemory(
            experiences=experiences,
            strategy=experience_memory_strategy,
            embedder=embedder_dict[embedder](),
            encoder=enc
        ),
        insight_memory=ExpeLInsightMemory(
            max_num_insights=max_insights,
            leeway=leeway
        ),
        success_batch_size=success_batch_size
    )

    run = wandb.init(
        project=benchmark, 
        entity="agential",
        config={
            "model": model,
            "eval_model": eval_model,
            "seed": seed,
            
        },
        group=method_name,
        tags=[f"method={method_name}", f"model={model}", f"eval_model={eval_model}", f"seed={seed}"],
    )

