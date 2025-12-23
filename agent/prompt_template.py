import json


##### system prompt template #####
# def generate_reduction_system_prompt():
#     prompt_template = "You are an AI assistant in an open-world survival game. I need you help me filter out the information from the game mechanics that meets the following criteria: (1) related to achieving long-term goal; (2) related to survival. The format of your reply should be:\n# Game Mechanics\n{your filtered game mechanics}\nDo not summarize or rewrite them, and do not include any additional content (such as your reasoning). "
#     return prompt_template


def generate_plan_system_prompt(plan_response_format, game_state=None):
    plan_response_format = json.dumps(plan_response_format, indent=4)
    if game_state:
        prompt_template = f"You are an AI assistant in an open-world survival game. I need you help me generate a plan for achieving my long-term goal. I will provide my long-term goal, descriptions of the game mechanics and the current game state (provided as JSON)."
    else:
        prompt_template = f"You are an AI assistant in an open-world survival game. I need you help me generate a plan for achieving my long-term goal. I will provide my long-term goal, descriptions of the game mechanics. "
    prompt_template += f"Your entire response must be a single valid JSON object in the following format:\n{plan_response_format}\nDo not include any text outside of the JSON object.\nNote: *Survival* is an absolute priority. "
    example = ""
    return prompt_template


def generate_task_system_prompt(task_response_format, strategies=None, previous_task=None):
    task_response_format = json.dumps(task_response_format, indent=4)
    prompt_template = f"You are an AI assistant in an open-world survival game. I need you help me set a reasonable short-term task to complete my long-term goal. I will provide my long-term goal, descriptions of the game mechanics and the current game state (provided as JSON)."
    if strategies:
        prompt_template += "What's more , I will also provide some strategies that can help you set the task. "
    if previous_task:
        prompt_template += (
            "You can set a new short-term task identical to the task in the previous step if you think it is still reasonable. "
        )
    prompt_template += f"Your entire response must be a single valid JSON object in the following format:\n{task_response_format}\nDo not include any text outside of the JSON object.\nNote: *Survival* is an absolute priority. "
    return prompt_template


def generate_action_system_prompt(action_response_format, action_type, player_role, use_fog=False, feedback=None):
    # player_role包括任务型(task)、生存型(individual)、竞争型(competitive)、合作型(cooperative)
    action_response_format = json.dumps(action_response_format, indent=4)
    if use_fog:
        prompt_template = "You are an AI assistant in an open-world survival game. In this game, players' survival is challenged by a lack of food or water, expanding toxic fog, aggressive NPCs, and even other hostile players. "
    else:
        prompt_template = "You are an AI assistant in an open-world survival game. In this game, players' survival is challenged by a lack of food or water, aggressive NPCs, and even other hostile players. "
    if player_role == "task":
        prompt_template += "I need you help me select an action for my game character to ensure my character's survival and achieve my long-term goal as quickly as possible. "
    elif player_role == "individual":
        prompt_template += (
            "I want my game character to survive as long as possible, and I don't care about the survival of other players. "
        )
    elif player_role == "competitive":
        prompt_template += "I want my game character to survive as long as possible. However, the survival resources are limited, so I want my character to stand out in the competition with other players and survive until the end. This may mean eliminating potential competitors, including other players or NPCs. "
    elif player_role == "cooperative":
        prompt_template += "I need you help me select an action from a set of available actions for my game character to ensure my character's survival. I believe that players can only overcome the survival challenges mentioned above by working together. Therefore, I hope the game character can help other players as much as possible. "
    else:
        raise ValueError(f"Unsupported player role: {player_role}")

    # if plan:
    #     prompt_template += "I will provide my long-term goal, my plan for achieving the long-term goal, descriptions of the game mechanics, the current game state, and the available actions. "
    # else:
    prompt_template += "I will provide the information needed for decision-making, including descriptions of the game mechanics and the current game state (provided as JSON). "

    # prompt_template += "The game state includes my region on the map, information about the resources and entities (NPCs or other players) within my field of view, and my inventory and skill levels. The field of view is divided into nine areas: center, north, northeast, east, southeast, south, southwest, west, and northwest. This division indicates the precise location of observed objects and assists players in determining the direction of exploration. "

    if use_fog:
        prompt_template += "Additionally, there is an expanding toxic fog in the game that poses a significant threat to my character's survival. Staying within the fog will gradually deplete my character's health, so it is crucial to avoid it and plan movements accordingly. "

    if action_type == "ml_action":
        prompt_template += "In this tick, you need to select an action from the available actions to harvest resources, combat or explore the game map. Available actions include harvesting resources, which allows the character to harvest resources located in the center area; attacking an entity, which lets the character move close and attack targets within the center area; and moving to a specific area, which enables the character to approach resources in other areas, get closer to or farther from certain entities, and explore the map. "

    elif action_type == "use":
        prompt_template += "In this tick, I have some items that can be equipped or used or unequipped. Choose an action from the action space to decide which items my character should use or equip or unequip. If you don't think there is anything worth using or equipping or unequipping right now, you can choose 'Use Nothing'. "
    elif action_type == "destroy":
        prompt_template += "In this tick, my inventory is full, which means I can't obtain any new items. Choose an action from the action space to destroy specific items and free up some space. If you don't think there is anything need to be destroyed right now, you can choose 'Destroy Nothing'. "
    elif action_type == "give":
        prompt_template += "In this tick, I have some unused or unequipped items in my inventory. You may consider whether to give them to nearby players, though this may not bring you any benefits. If you don't want to give anything to others right now, you can choose 'Give nothing to anyone'. "
    else:
        raise ValueError(f"Unsupported action type: {action_type}")

    if feedback:
        prompt_template += "In this step, I have already selected a candidate action (not yet executed). My verifier thinks it is not optimal and provides me with feedback. When you select action, take that feedback into consideration.\n"
    prompt_template += f"Your entire response must be a single valid JSON object in the following format:\n{action_response_format}\nDo not include any text outside of the JSON object. "
    return prompt_template


def generate_action_verify_system_prompt(
    verifier_response_format, action_type, player_role, plan=None, action_history=None, strategies=None
):
    verifier_response_format = json.dumps(verifier_response_format, indent=4)
    verifier_goal = "(1) ensure my survival"
    if player_role == "task":
        verifier_goal += " ; (2) complete my long-term goal as quickly as possible"
    else:
        verifier_goal += "; (2) consistent with my character design"
    if plan:
        verifier_goal += "; (3) follow my plan"
    verifier_goal += "."

    prompt_template = f"You are an AI assistant in an open-world survival game. I need you help me evaluate whether the candidate action I have selected can {verifier_goal} I will provide my long-term goal, descriptions of the game mechanics and the current game state (provided as JSON). "

    # prompt_template += "The game state includes my region on the map, information about the resources and entities (NPCs or other players) within my field of view, and my inventory and skill levels. The field of view is divided into nine areas: center, north, northeast, east, southeast, south, southwest, west, and northwest. This division indicates the precise location of observed objects and assists players in determining optimal movement directions."
    # if strategies:
    #     prompt_template += "What's more, I will also provide some strategies that can help you evaluate the action. "
    if action_type == "ml_action":
        prompt_template += "In this tick, I have selected a candidate action (not yet executed) from the available actions. Available actions include harvesting resources, which allows the character to harvest resources located in the center area; attacking an entity, which lets the character move close and attack targets within the center area; and moving to a specific area, which enables the character to approach resources in other areas, get closer to or farther from certain entities, and explore the map. "
    elif action_type == "use":
        prompt_template += "In this tick, I have selected a candidate action (not yet executed) from the available actions to decide which items my character should use or equip or unequip. "
    elif action_type == "destroy":
        prompt_template += "In this tick, I have selected a candidate action (not yet executed) from the available actions to destroy specific items and free up some space. "
    elif action_type == "give":
        pass
    else:
        raise ValueError(f"Unsupported action type: {action_type}")
    prompt_template += f"Respond with 'Yes' if the action is optimal in the available actions; otherwise, respond with 'No'. \nYour entire response must be a single valid JSON object in the following format:\n{verifier_response_format}\nDo not include any text outside of the JSON object. "
    return prompt_template


def generate_strategy_update_system_prompt(strategy_update_response_format):
    strategy_update_response_format = json.dumps(strategy_update_response_format, indent=4)
    prompt_template = f"You are an AI assistant in an open-world survival game. My game character has died in this step. I need you help me analyze the reason for the death of my character. Then, propose a strategy to prevent my character from dying for the same reason. Your entire response must be a single valid JSON object in the following format:\n{strategy_update_response_format}\nDo not include any text outside of the JSON object. "
    return prompt_template


##### user prompt template #####
def generate_plan_user_prompt(goal, game_mechanics, game_state=None):
    prompt_template = f"# My Long-term Goal\n{goal}\n\n# Game Mechanics\n{game_mechanics}\n\n"
    if game_state:
        prompt_template += f"# Game State\n{game_state}\n\n"
    return prompt_template


def generate_task_user_prompt(goal, game_mechanics, game_state, strategies=None, previous_task=None):
    prompt_template = f"# My Long-term Goal\n{goal}\n\n"
    prompt_template += f"# Game Mechanics\n{game_mechanics}\n\n# Game State\n{game_state}\n\n"
    if strategies:
        prompt_template += f"# Strategies\n{strategies}\n\n"
    if previous_task:
        prompt_template += f"# Previous Task\n{previous_task}"
    return prompt_template


def generate_action_user_prompt(
    game_mechanics,
    game_state,
    action_space,
    goal=None,
    plan=None,
    action_history=None,
    candidate_action=None,
    feedback=None,
):
    action_space = json.dumps(action_space, indent=4)
    if candidate_action:
        candidate_action = json.dumps(candidate_action, indent=4)
    prompt_template = ""
    if goal:
        prompt_template += f"# My Long-term Goal\n{goal}\n\n"
    prompt_template += f"# Game Introduction\n{game_mechanics}\n\n"
    if plan:
        prompt_template += f"# Plan\n{plan}\n\n"
    prompt_template += f"# Game Rule and Related Game State\n{game_state}\n\n"
    if action_history:
        action_history_len = len(action_history)
        action_history = "\n".join(action_history)
        prompt_template += f"# My Past {action_history_len} Actions\n{action_history}\n\n"
    # if strategies:
    #     prompt_template += f"# Strategies\n{strategies}\n\n"
    if candidate_action:
        prompt_template += f"# Candidate Action\n{candidate_action}\n\n"
    if feedback:
        prompt_template += f"# Action Feedback\n{feedback}\n\n"
    prompt_template += f"# Available Actions\n{action_space}\n\n"
    return prompt_template


def generate_action_verify_user_prompt(
    goal, game_mechanics, game_state, candidate_action, plan=None, action_history=None, strategies=None
):
    candidate_action = json.dumps(candidate_action, indent=4)
    prompt_template = f"# My Long-term Goal\n{goal}\n\n# Game Introduction\n{game_mechanics}\n\n"
    if plan:
        prompt_template += f"# Plan\n{plan}\n\n"
    # if strategies:
    #     prompt_template += f"# Strategies\n{strategies}\n\n"
    if action_history:
        action_history_len = len(action_history)
        action_history = "\n".join(action_history)
        prompt_template += f"# My Past {action_history_len} Actions\n{action_history}\n\n"
    prompt_template += f"# Game Rule and Related Game State\n{game_state}\n\n# Candidate Action\nIn this step, the candidate action I have selected (not yet executed) is:\n{candidate_action}"
    return prompt_template


# def generate_death_reason_user_prompt(game_mechanics, game_state):
#     prompt_template = f"# Game Mechanics\n{game_mechanics}\n\n# Game State\n{game_state}"
#     return prompt_template


def generate_strategy_update_user_prompt(game_mechanics, game_state):
    prompt_template = f"# Game Mechanics\n{game_mechanics}\n\n# Game State\n{game_state}"
    return prompt_template


# =========== Assistant Prompt ==========


def generate_assistant_system_prompt(action_response_format, player_role, assistant_role, use_fog=False):
    action_response_format = json.dumps(action_response_format, indent=4)
    if use_fog:
        prompt_template = "You are an AI assistant in an open-world survival game. In this game, players' survival is challenged by a lack of food or water, expanding toxic fog, aggressive NPCs, and even other hostile players. "
    else:
        prompt_template = "You are an AI assistant in an open-world survival game. In this game, players' survival is challenged by a lack of food or water, aggressive NPCs, and even other hostile players. "
    if player_role == "task":
        prompt_template += "I need you help me select an action for my game character to ensure my character's survival and achieve my long-term goal as quickly as possible. "
    else:
        prompt_template += "I want my game character to survive as long as possible. "
    prompt_template += "Now I am choosing an action for my game character. The available actions can be categorized into four types: maintaining survival, harvesting resources, exploration, and combat. "
    if assistant_role == "exploration":
        prompt_template += "Your goal is to persuade me as strongly as possible to choose an exploration action. Therefore, you need to select an appropriate exploration action and provide compelling reasons for choosing this action. To strengthen your persuasion, you should clearly explain—based on the game rules and the current game state—how the exploration action you choose will benefit progress toward achieving the goal. "

    elif assistant_role == "survival":
        prompt_template += "Your goal is to persuade me as strongly as possible to choose a survival action. Therefore, you need to select an appropriate survival action and provide compelling reasons for choosing this action. To strengthen your persuasion, you should clearly explain—based on the game rules and the current game state—how the survival action you choose will benefit progress toward achieving the goal. "

    elif assistant_role == "harvest":
        prompt_template += "Your goal is to persuade me as strongly as possible to choose a harvesting action. Therefore, you need to select an appropriate harvesting action and provide compelling reasons for choosing this action. To strengthen your persuasion, you should clearly explain—based on the game rules and the current game state—how the harvesting action you choose will benefit progress toward achieving the goal. "

    elif assistant_role == "combat":
        prompt_template += "Your goal is to persuade me as strongly as possible to choose a combat action. Therefore, you need to select an appropriate combat action and provide compelling reasons for choosing this action. To strengthen your persuasion, you should clearly explain—based on the game rules and the current game state—how the combat action you choose will benefit progress toward achieving the goal. "

    else:
        raise ValueError(f"Unsupported assistant role: {assistant_role}")

    # if plan:
    #     prompt_template += "I will provide my long-term goal, my plan for achieving the long-term goal, descriptions of the game mechanics, the current game state, and the available actions. "
    # else:
    prompt_template += "I will provide the information needed for decision-making, including descriptions of the game mechanics and the current game state (provided as JSON). "

    prompt_template += f"Your entire response must be a single valid JSON object in the following format:\n{action_response_format}\nDo not include any text outside of the JSON object. "
    return prompt_template


def generate_assistant_user_prompt(
    game_mechanics,
    game_state,
    action_space,
    goal=None,
):
    action_space = json.dumps(action_space, indent=4)
    if candidate_action:
        candidate_action = json.dumps(candidate_action, indent=4)
    prompt_template = ""
    if goal:
        prompt_template += f"# My Long-term Goal\n{goal}\n\n"
    prompt_template += f"# Game Introduction\n{game_mechanics}\n\n"
    prompt_template += f"# Game Rule and Related Game State\n{game_state}\n\n"
    prompt_template += f"# Available Actions\n{action_space}\n\n"
    return prompt_template
