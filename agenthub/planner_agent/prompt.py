import json
from typing import List, Tuple, Dict, Type

from opendevin.plan import Plan
from opendevin.action import Action
from opendevin.observation import Observation

from opendevin.action import (
    NullAction,
    CmdRunAction,
    CmdKillAction,
    BrowseURLAction,
    FileReadAction,
    FileWriteAction,
    AgentRecallAction,
    AgentThinkAction,
    AgentFinishAction,
    AgentSummarizeAction,
    AddSubtaskAction,
    CloseSubtaskAction,
)

from opendevin.observation import (
    NullObservation,
)

ACTION_TYPE_TO_CLASS: Dict[str, Type[Action]] = {
    "run": CmdRunAction,
    "kill": CmdKillAction,
    "browse": BrowseURLAction,
    "read": FileReadAction,
    "write": FileWriteAction,
    "recall": AgentRecallAction,
    "think": AgentThinkAction,
    "summarize": AgentSummarizeAction,
    "finish": AgentFinishAction,
    "add_subtask": AddSubtaskAction,
    "close_subtask": CloseSubtaskAction,
}

HISTORY_SIZE = 10

prompt = """
# Task
You're a diligent software engineer. You've been given the following task:

%(task)s

## Plan
As you complete this task, you're building a plan and keeping
track of your progress. Here's a JSON representation of your plan:
```json
%(plan)s
```

## History
Here is a recent history of actions you've taken in service of this plan,
as well as observations you've made.
```json
%(history)s
```

Your most recent action is at the bottom of that history.

## Action
What is your next thought or action? Your response must be in JSON format.

It must be an object, and it must contain two fields:
* `action`, which is one of the actions below
* `args`, which is a map of key-value pairs, specifying the arguments for that action

* `read` - reads the contents of a file. Arguments:
  * `path` - the path of the file to read
* `write` - writes the contents to a file. Arguments:
  * `path` - the path of the file to write
  * `contents` - the contents to write to the file
* `run` - runs a command. Arguments:
  * `command` - the command to run
  * `background` - if true, run the command in the background, so that other commands can be run concurrently. Useful for e.g. starting a server. You won't be able to see the logs. You don't need to end the command with `&`, just set this to true.
* `kill` - kills a background command
  * `id` - the ID of the background command to kill
* `browse` - opens a web page. Arguments:
  * `url` - the URL to open
* `think` - make a plan, set a goal, or record your thoughts. Arguments:
  * `thought` - the thought to record
* `add_subtask` - add a task to your plan. Arguments:
  * `parent` - the ID of the parent task
  * `goal` - the goal of the subtask
* `close_subtask` - close a subtask. Arguments:
  * `id` - the ID of the subtask to close
  * `completed` - set to true if the subtask is completed, false if it was abandoned
* `finish` - if you're absolutely certain that you've completed your task and have tested your work, use the finish action to stop working.

You MUST take time to think in between read, write, run, browse, and recall actions.
You should never act twice in a row without thinking. But if your last several
actions are all "think" actions, you should consider taking a different action.

What is your next thought or action? Again, you must reply with JSON, and only with JSON.

%(hint)s
"""

def get_prompt(plan: Plan, history: List[Tuple[Action, Observation]]):
    hint = ""
    plan_str = json.dumps(plan.task.to_dict(), indent=2)
    sub_history = history[-HISTORY_SIZE:]
    history_dicts = []
    for action, observation in sub_history:
        if not isinstance(action, NullAction):
            action_dict = action.to_dict()
            action_dict["action"] = convert_action(action_dict["action"])
            history_dicts.append(action_dict)
        if not isinstance(observation, NullObservation):
            observation_dict = observation.to_dict()
            observation_dict["observation"] = convert_observation(observation_dict["observation"])
            history_dicts.append(observation_dict)
    history_str = json.dumps(history_dicts, indent=2)
    return prompt % {
        'task': plan.main_goal,
        'plan': plan_str,
        'history': history_str,
        'hint': hint,
    }

def parse_response(response: str) -> Action:
    json_start = response.find("{")
    json_end = response.rfind("}") + 1
    response = response[json_start:json_end]
    action_dict = json.loads(response)
    if 'content' in action_dict:
        # The LLM gets confused here. Might as well be robust
        action_dict['contents'] = action_dict.pop('content')

    action = ACTION_TYPE_TO_CLASS[action_dict["action"]](**action_dict["args"])
    return action

def convert_action(action):
    if action == "CmdRunAction":
        action = "run"
    elif action == "CmdKillAction":
        action = "kill"
    elif action == "BrowseURLAction":
        action = "browse"
    elif action == "FileReadAction":
        action = "read"
    elif action == "FileWriteAction":
        action = "write"
    elif action == "AgentFinishAction":
        action = "finish"
    elif action == "AgentRecallAction":
        action = "recall"
    elif action == "AgentThinkAction":
        action = "think"
    elif action == "AgentSummarizeAction":
        action = "summarize"
    elif action == "AddSubtaskAction":
        action = "add_subtask"
    elif action == "CloseSubtaskAction":
        action = "close_subtask"
    return action

def convert_observation(observation):
    if observation == "UserMessageObservation":
        observation = "chat"
    elif observation == "AgentMessageObservation":
        observation = "chat"
    elif observation == "CmdOutputObservation":
        observation = "run"
    elif observation == "FileReadObservation":
        observation = "read"
    return observation