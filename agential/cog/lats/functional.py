"""Functional module for Language Agent Tree Search (LATS)."""

import numpy as np
import openai
import requests

from typing import Dict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages.human import HumanMessage
from langchain_core.prompts.prompt import PromptTemplate


def _build_standard_prompt(
    question: str,
    trajectory: str,
    thought: str,
    prompt: str,
    additional_keys: Dict[str, str] = {},
) -> str:
    """Builds a prompt for questioning the agent using a template.

    Parameters:
        question (str): The question to be answered by the agent.
        trajectory (str): The trajectory taken by the agent. 
        thought (str): The agent's thought.
        prompt (str): Prompt template string.
        additional_keys (Dict[str, str]): Additional keys to format the prompt. Defaults to {}.

    Returns:
        str: A formatted prompt ready for use with the language model.
    """
    prompt = PromptTemplate.from_template(prompt).format(
        question=question, trajectory=trajectory, thought=thought, **additional_keys
    )
    return prompt
    

def _prompt_standard():
    pass

def _build_cot_prompt():
    pass

def _prompt_cot():
    pass

def _build_reflection_prompt():
    pass

def _prompt_reflection():
    pass

def _build_value_prompt():
    pass

def _prompt_value():
    pass


















global reflection_map
global failed_trajectories
reflection_map = []
failed_trajectories = []

class Node:
    def __init__(self, state, question, parent=None):
        self.state = {'thought': '', 'action': '', 'observation': ''} if state is None else state
        self.parent = parent
        self.question = question
        self.children = []
        self.visits = 0
        self.value = 0
        self.depth = 0 if parent is None else parent.depth + 1
        self.is_terminal = False
        self.reward = 0

    def uct(self):
        if self.visits == 0:
            return self.value
        return self.value / self.visits + np.sqrt(2 * np.log(self.parent.visits) / self.visits)
    
def upward_traversal(node):
    nodes = []
    while node:
        nodes.append(node)
        node = node.parent
    return list(reversed(nodes))

def generate_prompt(traversed_nodes):
    trajectory = []

    for node in traversed_nodes:
        if node.depth > 0:
            if node.state['thought']:
                trajectory.append(f"Thought {node.depth}: {node.state['thought']}")
            if node.state['action']:
                trajectory.append(f"Action {node.depth}: {node.state['action']}")
            if node.state['observation']:
                trajectory.append(f"Observation {node.depth}: {node.state['observation']}")

    return '\n'.join(trajectory)


def select_node(node: Node):
    while node and node.children:
        terminal_children = [child for child in node.children if child.is_terminal]

        if len(terminal_children) == len(node.children):
            if node.parent:  
                node.parent.children.remove(node)
            node = node.parent  
            continue  

        for child in terminal_children:
            if child.reward == 1:
                return child
        
        node = max([child for child in node.children if not child.is_terminal], key=lambda child: child.uct(), default=None)

    return node

def get_unique_trajectories(failed_trajectories, num=5):
    unique_trajectories = []
    seen_final_answers = set()
    for traj in failed_trajectories:
        final_answer = traj.get('final_answer')
        if final_answer not in seen_final_answers:
            unique_trajectories.append(generate_prompt(traj['trajectory']))
            seen_final_answers.add(final_answer)
        if len(unique_trajectories) >= num:
            break
    return unique_trajectories

def gpt(prompt, model="gpt-3.5-turbo", temperature=1.0, max_tokens=100, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    outputs = []
    
    while n > 0:
        cnt = min(n, 20)
        n -= cnt
        res = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, n=cnt, stop=stop)
        outputs.extend([choice["message"]["content"] for choice in res["choices"]])
    
    return outputs

def get_samples(task, x, question, trajectory, thought, additional_keys, n_generate_sample, prompt_sample, stop):
    global failed_trajectories
    global reflection_map
    unique_trajectories = get_unique_trajectories(failed_trajectories)
    if len(unique_trajectories) > len(reflection_map) and len(unique_trajectories) < 4:
        print("generating reflections")
        reflection_map = task.generate_self_reflection(unique_trajectories, x)
    if prompt_sample == 'standard':
        prompt = _build_standard_prompt(question, trajectory, thought, prompt, additional_keys)
    elif prompt_sample == 'cot':
        prompt = task.cot_prompt_wrap(x, thought, reflection_map)
    else:
        raise ValueError(f'prompt_sample {prompt_sample} not recognized')
    samples = gpt(prompt, n=n_generate_sample, stop=stop)
    return [thought + _ for _ in samples]

def generate_new_states(node, prompt_sample, task, n):
    global failed_trajectories
    traversed_nodes = upward_traversal(node)
    prompt = node.question
    trajectory = generate_prompt(traversed_nodes)
    additional_keys = Dict[str, str] = {}
    sampled_actions = get_samples(task, prompt, prompt, trajectory, f"Thought {node.depth + 1}: ", additional_keys, n, prompt_sample=prompt_sample, stop="Observation")
    tried_actions = []
    
    unique_states = {}  # Store unique states here
    for action in sampled_actions:

        thought_line = next((line.split(":")[1].strip() for line in action.split("\n") if line.startswith(f"Thought {node.depth + 1}")), '')
        action_line = next((line.split(":")[1].strip() for line in action.split("\n") if line.startswith("Action") and ":" in line), None)

        # Use thought and action to form a unique key
        unique_key = f"{thought_line}::{action_line}"
        
        if unique_key in unique_states:
            continue  # Skip if this state already exists

        tried_actions.append(action_line)
        
        if action_line:
            action_type = action_line.split('[')[0] if '[' in action_line else action_line
            action_param = action_line.split('[')[1].split(']')[0] if '[' in action_line else ""

            obs, r, done, info = env.step(f"{action_type.lower()}[{action_param}]")

            # Update the new state dictionary
            new_state = {
                'thought': thought_line,
                'action': action_line,
                'observation': obs
            }

            new_node = Node(state=new_state, question=node.question, parent=node)
            new_node.is_terminal = r == 1 or done
            new_node.reward = r
            new_node.depth = node.depth + 1

            unique_states[unique_key] = new_node  # Add this state to unique_states

            if new_node.is_terminal and r == 0:
                traversed_nodes = upward_traversal(new_node)
                failed_trajectories.append({'trajectory': traversed_nodes, 'final_answer': f"{action_type.lower()}[{action_param}]"})

    return list(unique_states.values())  # Return unique nodes as a list


def expand_node(node, prompt_sample, task, n_generate_sample, depth_limit=7):
    if node.depth >= depth_limit:
        node.is_terminal = True
        return []
    children_nodes = generate_new_states(node, prompt_sample, task, n_generate_sample)
    return children_nodes

def get_value(task, x, y, n_evaluate_sample, cache_value=True):
    global reflection_map
    global failed_trajectories
    
    unique_trajectories = get_unique_trajectories(failed_trajectories)
    value_prompt = task.value_prompt_wrap(x, y, unique_trajectories, reflection_map)
    if cache_value and value_prompt in task.value_cache:
        return task.value_cache[value_prompt]
    value_outputs = gpt(value_prompt, n=n_evaluate_sample, stop=None)
    value = task.value_outputs_unwrap(value_outputs)
    if cache_value:
        task.value_cache[value_prompt] = value
    return value

def get_values(task, x, ys, n_evaluate_sample, cache_value=True):
    values = []
    local_value_cache = {}
    for y in ys:  # each partial output
        if y in local_value_cache:  # avoid duplicate candidates
            value = 0
        else:    
            value = get_value(task, x, y, n_evaluate_sample, cache_value=cache_value)
            local_value_cache[y] = value
        values.append(value)
    return values

def evaluate_node(node, task, n_evaluate_sample):
    child_prompts = [child.question + generate_prompt(upward_traversal(child)) for child in node.children if not child.is_terminal]
    votes = get_values(task, node.question, child_prompts, n_evaluate_sample)
        
    # Pre-allocate votes list
    votes = votes + [0] * (len(node.children) - len(votes))
    for i, child in enumerate(node.children):
        child.value = votes[i] 

    return sum(votes) / len(votes) if votes else 0

def rollout(node, task, n_evaluate_sample, prompt_sample, max_depth=4):
    depth = node.depth
    n = 5
    rewards = [0]
    while not node.is_terminal and depth < max_depth:
        new_states = []
        values = []
        while len(new_states) == 0:
            new_states = generate_new_states(node, prompt_sample, task, n)

        for state in new_states:
            if state.is_terminal:
                return state.reward, state
                
        child_prompts = [child.question + generate_prompt(upward_traversal(child)) for child in new_states if not child.is_terminal and child is not None]
        while len(values) == 0:
            values = get_values(task, node.question, child_prompts, n_evaluate_sample)
        max_value_index = values.index(max(values))
        rewards.append(max(values))
        node = new_states[max_value_index] 
        depth += 1
        if depth == max_depth:
            rewards = [-1]
    
    return sum(rewards) / len(rewards), node

def backpropagate(node, value):
    while node:
        node.visits += 1
        if node.is_terminal:
            if node.reward == 0:
                node.value = (node.value * (node.visits - 1) + (-1)) / node.visits
            else:
                node.value = (node.value * (node.visits - 1) + value) / node.visits
        else:
            node.value = (node.value * (node.visits - 1) + value) / node.visits

        node = node.parent

def preorder_traversal(node):
        nodes = [node]
        for child in node.children:
            nodes.extend(preorder_traversal(child))
        return nodes