"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: plan.py
Description: This defines the "Plan" module for generative agents. 
"""
import datetime
import json
import math
import os
import random
import sys
import time
sys.path.append('../../')

from global_methods import *
from persona.prompt_template.run_gpt_prompt import *
from persona.cognitive_modules.retrieve import *
from persona.cognitive_modules.converse import *
from utils import fs_storage, fs_temp_storage

##############################################################################
# CHAPTER 2: Generate
##############################################################################

def generate_wake_up_hour(persona):
  """
  Generates the time when the persona wakes up. This becomes an integral part
  of our process for generating the persona's daily plan.
  
  Persona state: identity stable set, lifestyle, first_name

  INPUT: 
    persona: The Persona class instance 
  OUTPUT: 
    an integer signifying the persona's wake up hour
  EXAMPLE OUTPUT: 
    8
  """
  if debug: print ("GNS FUNCTION: <generate_wake_up_hour>")
  return int(run_gpt_prompt_wake_up_hour(persona)[0])


def generate_first_daily_plan(persona, wake_up_hour): 
  """
  Generates the daily plan for the persona. 
  Basically the long term planning that spans a day. Returns a list of actions
  that the persona will take today. Usually comes in the following form: 
  'wake up and complete the morning routine at 6:00 am', 
  'eat breakfast at 7:00 am',.. 
  Note that the actions come without a period. 

  Persona state: identity stable set, lifestyle, cur_data_str, first_name

  INPUT: 
    persona: The Persona class instance 
    wake_up_hour: an integer that indicates when the hour the persona wakes up 
                  (e.g., 8)
  OUTPUT: 
    a list of daily actions in broad strokes.
  EXAMPLE OUTPUT: 
    ['wake up and complete the morning routine at 6:00 am', 
     'have breakfast and brush teeth at 6:30 am',
     'work on painting project from 8:00 am to 12:00 pm', 
     'have lunch at 12:00 pm', 
     'take a break and watch TV from 2:00 pm to 4:00 pm', 
     'work on painting project from 4:00 pm to 6:00 pm', 
     'have dinner at 6:00 pm', 'watch TV from 7:00 pm to 8:00 pm']
  """
  if debug: print ("GNS FUNCTION: <generate_first_daily_plan>")
  return run_gpt_prompt_daily_plan(persona, wake_up_hour)[0]


def generate_hourly_schedule(persona, wake_up_hour): 
  """
  Based on the daily req, creates an hourly schedule -- one hour at a time. 
  The form of the action for each of the hour is something like below: 
  "sleeping in her bed"
  
  The output is basically meant to finish the phrase, "x is..."

  Persona state: identity stable set, daily_plan

  INPUT: 
    persona: The Persona class instance 
    persona: Integer form of the wake up hour for the persona.  
  OUTPUT: 
    a list of activities and their duration in minutes: 
  EXAMPLE OUTPUT: 
    [['sleeping', 360], ['waking up and starting her morning routine', 60], 
     ['eating breakfast', 60],..
  """
  if debug: print ("GNS FUNCTION: <generate_hourly_schedule>")

  hour_str = ["00:00 AM", "01:00 AM", "02:00 AM", "03:00 AM", "04:00 AM", 
              "05:00 AM", "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM", 
              "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", 
              "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM",
              "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM"]
  n_m1_activity = []
  diversity_repeat_count = 3
  for i in range(diversity_repeat_count): 
    n_m1_activity_set = set(n_m1_activity)
    if len(n_m1_activity_set) < 5: 
      n_m1_activity = []
      for count, curr_hour_str in enumerate(hour_str): 
        if wake_up_hour > 0: 
          n_m1_activity += ["sleeping"]
          wake_up_hour -= 1
        else: 
          n_m1_activity += [run_gpt_prompt_generate_hourly_schedule(
                          persona, curr_hour_str, n_m1_activity, hour_str)[0]]
  
  # Step 1. Compressing the hourly schedule to the following format: 
  # The integer indicates the number of hours. They should add up to 24. 
  # [['sleeping', 6], ['waking up and starting her morning routine', 1], 
  # ['eating breakfast', 1], ['getting ready for the day', 1], 
  # ['working on her painting', 2], ['taking a break', 1], 
  # ['having lunch', 1], ['working on her painting', 3], 
  # ['taking a break', 2], ['working on her painting', 2], 
  # ['relaxing and watching TV', 1], ['going to bed', 1], ['sleeping', 2]]
  _n_m1_hourly_compressed = []
  prev = None 
  prev_count = 0
  for i in n_m1_activity: 
    if i != prev:
      prev_count = 1 
      _n_m1_hourly_compressed += [[i, prev_count]]
      prev = i
    else: 
      if _n_m1_hourly_compressed: 
        _n_m1_hourly_compressed[-1][1] += 1

  # Step 2. Expand to min scale (from hour scale)
  # [['sleeping', 360], ['waking up and starting her morning routine', 60], 
  # ['eating breakfast', 60],..
  n_m1_hourly_compressed = []
  for task, duration in _n_m1_hourly_compressed: 
    n_m1_hourly_compressed += [[task, duration*60]]

  return n_m1_hourly_compressed


def generate_task_decomp(persona, task, duration): 
  """
  A few shot decomposition of a task given the task description 

  Persona state: identity stable set, curr_date_str, first_name

  INPUT: 
    persona: The Persona class instance 
    task: the description of the task at hand in str form
          (e.g., "waking up and starting her morning routine")
    duration: an integer that indicates the number of minutes this task is 
              meant to last (e.g., 60)
  OUTPUT: 
    a list of list where the inner list contains the decomposed task 
    description and the number of minutes the task is supposed to last. 
  EXAMPLE OUTPUT: 
    [['going to the bathroom', 5], ['getting dressed', 5], 
     ['eating breakfast', 15], ['checking her email', 5], 
     ['getting her supplies ready for the day', 15], 
     ['starting to work on her painting', 15]] 

  """
  if debug: print ("GNS FUNCTION: <generate_task_decomp>")
  return run_gpt_prompt_task_decomp(persona, task, duration)[0]


def generate_action_sector(act_desp, persona, maze): 
  """TODO 
  Given the persona and the task description, choose the action_sector. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance 
  OUTPUT: 
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT: 
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_sector>")
  return run_gpt_prompt_action_sector(act_desp, persona, maze)[0]


def generate_action_arena(act_desp, persona, maze, act_world, act_sector): 
  """TODO 
  Given the persona and the task description, choose the action_arena. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance 
  OUTPUT: 
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT: 
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_arena>")
  return run_gpt_prompt_action_arena(act_desp, persona, maze, act_world, act_sector)[0]


def generate_action_game_object(act_desp, act_address, persona, maze):
  """TODO
  Given the action description and the act address (the address where
  we expect the action to task place), choose one of the game objects. 

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    act_address: the arena where the action will take place: 
               (e.g., "dolores double studio:double studio:bedroom 2")
    persona: The Persona class instance 
  OUTPUT: 
    act_game_object: 
  EXAMPLE OUTPUT: 
    "bed"
  """
  if debug: print ("GNS FUNCTION: <generate_action_game_object>")
  if not persona.s_mem.get_str_accessible_arena_game_objects(act_address): 
    return "<random>"
  return run_gpt_prompt_action_game_object(act_desp, persona, maze, act_address)[0]


def generate_action_pronunciatio(act_desp, persona): 
  """TODO 
  Given an action description, creates an emoji string description via a few
  shot prompt. 

  Does not really need any information from persona. 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_pronunciatio>")
  try: 
    x = run_gpt_prompt_pronunciatio(act_desp, persona)[0]
  except: 
    x = "🙂"

  if not x: 
    return "🙂"
  return x


def generate_action_event_triple(act_desp, persona): 
  """TODO 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_act_obj_desc(act_game_object, act_desp, persona): 
  if debug: print ("GNS FUNCTION: <generate_act_obj_desc>")
  return run_gpt_prompt_act_obj_desc(act_game_object, act_desp, persona)[0]


def generate_act_obj_event_triple(act_game_object, act_obj_desc, persona): 
  if debug: print ("GNS FUNCTION: <generate_act_obj_event_triple>")
  return run_gpt_prompt_act_obj_event_triple(act_game_object, act_obj_desc, persona)[0]


def generate_convo(maze, init_persona, target_persona): 
  curr_loc = maze.access_tile(init_persona.scratch.curr_tile)

  # convo = run_gpt_prompt_create_conversation(init_persona, target_persona, curr_loc)[0]
  # convo = agent_chat_v1(maze, init_persona, target_persona)
  convo = agent_chat_v2(maze, init_persona, target_persona)
  all_utt = ""

  for row in convo: 
    speaker = row[0]
    utt = row[1]
    all_utt += f"{speaker}: {utt}\n"

  convo_length = math.ceil(int(len(all_utt)/8) / 30)

  if debug: print ("GNS FUNCTION: <generate_convo>")
  return convo, convo_length


def generate_convo_summary(persona, convo): 
  convo_summary = run_gpt_prompt_summarize_conversation(persona, convo)[0]
  return convo_summary


def generate_decide_to_talk(init_persona, target_persona, retrieved): 
  x =run_gpt_prompt_decide_to_talk(init_persona, target_persona, retrieved)[0]
  if debug: print ("GNS FUNCTION: <generate_decide_to_talk>")

  if x == "yes": 
    return True
  else: 
    return False


def generate_decide_to_react(init_persona, target_persona, retrieved): 
  if debug: print ("GNS FUNCTION: <generate_decide_to_react>")
  return run_gpt_prompt_decide_to_react(init_persona, target_persona, retrieved)[0]


def generate_new_decomp_schedule(persona, inserted_act, inserted_act_dur,  start_hour, end_hour): 
  # Step 1: Setting up the core variables for the function. 
  # <p> is the persona whose schedule we are editing right now. 
  p = persona
  # <today_min_pass> indicates the number of minutes that have passed today. 
  today_min_pass = (int(p.scratch.curr_time.hour) * 60 
                    + int(p.scratch.curr_time.minute) + 1)
  
  # Step 2: We need to create <main_act_dur> and <truncated_act_dur>. 
  # These are basically a sub-component of <f_daily_schedule> of the persona,
  # but focusing on the current decomposition. 
  # Here is an example for <main_act_dur>: 
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (uses the restroom)', 5]
  # ['wakes up and completes her morning routine (washes her ...)', 10]
  # ['wakes up and completes her morning routine (makes her bed)', 5]
  # ['wakes up and completes her morning routine (eats breakfast)', 15]
  # ['wakes up and completes her morning routine (gets dressed)', 10]
  # ['wakes up and completes her morning routine (leaves her ...)', 5]
  # ['wakes up and completes her morning routine (starts her ...)', 5]
  # ['preparing for her day (waking up at 6am)', 5]
  # ['preparing for her day (making her bed)', 5]
  # ['preparing for her day (taking a shower)', 15]
  # ['preparing for her day (getting dressed)', 5]
  # ['preparing for her day (eating breakfast)', 10]
  # ['preparing for her day (brushing her teeth)', 5]
  # ['preparing for her day (making coffee)', 5]
  # ['preparing for her day (checking her email)', 5]
  # ['preparing for her day (starting to work on her painting)', 5]
  # 
  # And <truncated_act_dur> concerns only until where an event happens. 
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 2]
  main_act_dur = []
  truncated_act_dur = []
  dur_sum = 0 # duration sum
  count = 0 # enumerate count
  truncated_fin = False 

  print ("DEBUG::: ", persona.scratch.name)
  for act, dur in p.scratch.f_daily_schedule: 
    if (dur_sum >= start_hour * 60) and (dur_sum < end_hour * 60): 
      main_act_dur += [[act, dur]]
      if dur_sum <= today_min_pass:
        truncated_act_dur += [[act, dur]]
      elif dur_sum > today_min_pass and not truncated_fin: 
        # We need to insert that last act, duration list like this one: 
        # e.g., ['wakes up and completes her morning routine (wakes up...)', 2]
        truncated_act_dur += [[p.scratch.f_daily_schedule[count][0], 
                               dur_sum - today_min_pass]] 
        truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass) ######## DEC 7 DEBUG;.. is the +1 the right thing to do??? 
        # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass + 1) ######## DEC 7 DEBUG;.. is the +1 the right thing to do??? 
        print ("DEBUG::: ", truncated_act_dur)

        # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass) ######## DEC 7 DEBUG;.. is the +1 the right thing to do??? 
        truncated_fin = True
    dur_sum += dur
    count += 1

  persona_name = persona.name 
  main_act_dur = main_act_dur

  x = truncated_act_dur[-1][0].split("(")[0].strip() + " (on the way to " + truncated_act_dur[-1][0].split("(")[-1][:-1] + ")"
  truncated_act_dur[-1][0] = x 

  if "(" in truncated_act_dur[-1][0]: 
    inserted_act = truncated_act_dur[-1][0].split("(")[0].strip() + " (" + inserted_act + ")"

  # To do inserted_act_dur+1 below is an important decision but I'm not sure
  # if I understand the full extent of its implications. Might want to 
  # revisit. 
  truncated_act_dur += [[inserted_act, inserted_act_dur]]
  start_time_hour = (datetime.datetime(2022, 10, 31, 0, 0) 
                   + datetime.timedelta(hours=start_hour))
  end_time_hour = (datetime.datetime(2022, 10, 31, 0, 0) 
                   + datetime.timedelta(hours=end_hour))

  if debug: print ("GNS FUNCTION: <generate_new_decomp_schedule>")
  return run_gpt_prompt_new_decomp_schedule(persona, 
                                            main_act_dur, 
                                            truncated_act_dur, 
                                            start_time_hour,
                                            end_time_hour,
                                            inserted_act,
                                            inserted_act_dur)[0]


##############################################################################
# SURVEY REGISTRY
# To add a new survey:
#   1. Create a prompt template in v3_ChatGPT/
#   2. Add run_gpt_prompt_<name>() in run_gpt_prompt.py
#   3. Append a dict below with: name, func, frequency
#      frequency options: "daily" | "weekly" | "biweekly" | "monthly"
##############################################################################

SURVEY_REGISTRY = [
  {
    "name":      "daily_survey",
    "func":      run_gpt_prompt_daily_survey,
    "frequency": "daily",
  },
  # {
  #   "name":      "weekly_survey",
  #   "func":      run_gpt_prompt_weekly_survey,
  #   "frequency": "weekly",
  # },
  # {
  #   "name":      "biweekly_survey",
  #   "func":      run_gpt_prompt_biweekly_survey,
  #   "frequency": "biweekly",
  # },
  # {
  #   "name":      "monthly_survey",
  #   "func":      run_gpt_prompt_monthly_survey,
  #   "frequency": "monthly",
  # },
]


def _survey_is_due(frequency, yesterday, survey_file):
  """
  Returns True if a survey of the given frequency should run today.

  For "daily" surveys this is always True (the call site already gates on
  new_day == "New day").  For longer frequencies we check how many days
  have elapsed since the last recorded entry in the survey file.
  """
  if frequency == "daily":
    return True

  days_required = {"weekly": 7, "biweekly": 14, "monthly": 30}[frequency]

  if not os.path.isfile(survey_file):
    return True

  try:
    with open(survey_file) as f:
      entries = json.load(f)
    if not entries:
      return True
    last_date = datetime.datetime.strptime(entries[-1]["sim_time"], "%Y-%m-%d")
    return (yesterday - last_date).days >= days_required
  except (json.JSONDecodeError, KeyError, ValueError):
    return True


def _run_surveys(persona, sim_code):
  """
  Iterates SURVEY_REGISTRY and runs every survey that is due for <persona>.
  Results are appended to:
    {fs_storage}/{sim_code}/surveys/{persona_name}/{survey_name}.json
  """
  yesterday = persona.scratch.curr_time - datetime.timedelta(days=1)
  survey_dir = os.path.join(fs_storage, sim_code, "surveys", persona.scratch.name)
  os.makedirs(survey_dir, exist_ok=True)

  for survey in SURVEY_REGISTRY:
    survey_file = os.path.join(survey_dir, f"{survey['name']}.json")

    if not _survey_is_due(survey["frequency"], yesterday, survey_file):
      continue

    survey_response, _ = survey["func"](persona)

    record = {
      "persona":  persona.scratch.name,
      "date":     yesterday.strftime("%A %B %d"),
      "sim_time": yesterday.strftime("%Y-%m-%d"),
      "responses": survey_response,
    }

    existing = []
    if os.path.isfile(survey_file):
      with open(survey_file) as f:
        try:
          existing = json.load(f)
        except json.JSONDecodeError:
          existing = []

    existing.append(record)
    with open(survey_file, "w") as f:
      json.dump(existing, f, indent=2)


def should_generate_weekly_work_survey(persona):
  """
  Returns True once per completed simulated week.
  The survey is generated on Mondays and reflects on the week that ended the
  day before.
  """
  if not persona.scratch.curr_time:
    return False

  if persona.scratch.curr_time.weekday() != 0:
    return False

  week_end = persona.scratch.curr_time - datetime.timedelta(days=1)
  week_end_key = week_end.strftime("%Y-%m-%d")
  sim_code_file = os.path.join(fs_temp_storage, "curr_sim_code.json")
  if not os.path.isfile(sim_code_file):
    return False

  with open(sim_code_file, "r") as f:
    sim_code = json.load(f)["sim_code"]

  survey_file = os.path.join(
    fs_storage, sim_code, "weekly_surveys", persona.scratch.name,
    "responses.json")

  if os.path.isfile(survey_file):
    with open(survey_file, "r") as f:
      try:
        existing = json.load(f)
      except json.JSONDecodeError:
        existing = []
    for record in reversed(existing):
      if record.get("week_end") == week_end_key:
        return False

  return True


def generate_weekly_work_survey(persona):
  """
  Runs the work survey for <persona> and appends the result to:
    {fs_storage}/{sim_code}/weekly_surveys/{persona.scratch.name}/responses.json
  """
  if not should_generate_weekly_work_survey(persona):
    return

  sim_code_file = os.path.join(fs_temp_storage, "curr_sim_code.json")
  with open(sim_code_file, "r") as f:
    sim_code = json.load(f)["sim_code"]

  week_end = persona.scratch.curr_time - datetime.timedelta(days=1)
  week_start = week_end - datetime.timedelta(days=6)
  survey_week_key = week_end.strftime("%G-W%V")
  survey_response, _ = run_gpt_prompt_weekly_work_survey(persona)

  record = {
    "persona": persona.scratch.name,
    "survey_date": week_end.strftime("%Y-%m-%d"),
    "survey_week": survey_week_key,
    "week_start": week_start.strftime("%Y-%m-%d"),
    "week_end": week_end.strftime("%Y-%m-%d"),
    "recorded_at": persona.scratch.curr_time.strftime("%Y-%m-%d %H:%M:%S"),
    "responses": survey_response,
  }

  survey_dir = os.path.join(fs_storage, sim_code, "weekly_surveys",
                            persona.scratch.name)
  os.makedirs(survey_dir, exist_ok=True)
  survey_file = os.path.join(survey_dir, "responses.json")

  existing = []
  if os.path.isfile(survey_file):
    with open(survey_file, "r") as f:
      try:
        existing = json.load(f)
      except json.JSONDecodeError:
        existing = []

  existing.append(record)
  with open(survey_file, "w") as f:
    json.dump(existing, f, indent=2)


def _employment_values_match(persona, left, right):
  left = persona.scratch._normalize_employment_value(left)
  right = persona.scratch._normalize_employment_value(right)

  if left is None or right is None:
    return left == right
  return left.casefold() == right.casefold()


def _profile_has_active_job(profile):
  return (profile.get("employment_status") in ["employed", "informal_work"]
          or any(profile.get(key) for key in ["job_title", "employer",
                                              "workplace"]))


def _summarize_employment_profile(persona, profile):
  first_name = persona.scratch.get_str_firstname() or persona.scratch.name
  status = profile.get("employment_status")
  job_title = profile.get("job_title")
  employer = profile.get("employer")
  workplace = profile.get("workplace")

  if status == "student":
    description = f"{first_name} is currently a student"
  elif status == "caregiver":
    description = f"{first_name}'s primary role is caregiving"
  elif status == "retired":
    description = f"{first_name} is currently retired"
  elif status == "informal_work":
    description = f"{first_name} is currently doing informal work"
  elif status:
    description = f"{first_name} is currently {status}"
  elif job_title or employer or workplace:
    description = f"{first_name} is currently employed"
  else:
    description = f"{first_name}'s employment situation is unspecified"

  if job_title:
    description += f" as {job_title}"
  if employer:
    description += f" at {employer}"
  if workplace and workplace != employer:
    description += f" in {workplace}"

  return description


def _classify_employment_reconciliation_event(persona,
                                              current_profile,
                                              inferred_profile):
  current_has_active_job = _profile_has_active_job(current_profile)
  inferred_has_active_job = _profile_has_active_job(inferred_profile)

  if inferred_has_active_job and not current_has_active_job:
    return "job_acquisition"
  if not inferred_has_active_job and current_has_active_job:
    return "termination"
  return "transition"


def reconcile_currently_with_employment_state(persona):
  """
  Reconcile the updated narrative status against structured employment state.
  If the current narrative implies a meaningful job-state change, log a
  structured employment event so downstream prompts see synchronized state.
  """
  inferred_profile, _ = run_gpt_prompt_employment_reconciliation(persona)
  if not isinstance(inferred_profile, dict):
    return

  inferred_profile = persona.scratch._normalize_employment_profile(
    inferred_profile)
  if not any(inferred_profile.values()):
    return

  current_profile = persona.scratch.get_current_employment_profile()
  meaningful_change = False
  for key in ["employment_status", "job_title", "employer", "workplace"]:
    inferred_value = inferred_profile.get(key)
    if inferred_value is None:
      continue
    if not _employment_values_match(persona, current_profile.get(key),
                                    inferred_value):
      meaningful_change = True
      break

  if not meaningful_change:
    return

  event_type = _classify_employment_reconciliation_event(
    persona, current_profile, inferred_profile)
  previous_summary = _summarize_employment_profile(persona, current_profile)
  current_summary = _summarize_employment_profile(persona, inferred_profile)

  if event_type == "job_acquisition":
    description = (f"Based on {persona.scratch.name}'s updated status, "
                   f"the current employment picture is: {current_summary}.")
  elif event_type == "termination":
    description = (f"Based on {persona.scratch.name}'s updated status, "
                   f"the prior employment picture '{previous_summary}' is no "
                   f"longer accurate; the current employment picture is: "
                   f"{current_summary}.")
  else:
    description = (f"Based on {persona.scratch.name}'s updated status, "
                   f"the employment picture changed from "
                   f"'{previous_summary}' to '{current_summary}'.")

  persona.scratch.log_employment_event(
    event_type,
    description,
    employer=inferred_profile.get("employer"),
    job_title=inferred_profile.get("job_title"),
    workplace=inferred_profile.get("workplace"),
    employment_status=inferred_profile.get("employment_status"),
    metadata={
      "source": "daily_currently_reconciliation",
      "currently": persona.scratch.currently,
      "previous_profile": current_profile,
      "inferred_profile": inferred_profile,
    })


##############################################################################
# CHAPTER 3: Plan
##############################################################################

def revise_identity(persona): 
  p_name = persona.scratch.name

  focal_points = [f"{p_name}'s plan for {persona.scratch.get_str_curr_date_str()}.",
                  f"Important recent events for {p_name}'s life."]
  retrieved = new_retrieve(persona, focal_points)

  statements = "[Statements]\n"
  for key, val in retrieved.items():
    for i in val: 
      statements += f"{i.created.strftime('%A %B %d -- %H:%M %p')}: {i.embedding_key}\n"

  # print (";adjhfno;asdjao;idfjo;af", p_name)
  plan_prompt = statements + "\n"
  plan_prompt += f"Given the statements above, is there anything that {p_name} should remember as they plan for"
  plan_prompt += f" *{persona.scratch.curr_time.strftime('%A %B %d')}*? "
  plan_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement)\n\n"
  plan_prompt += f"Write the response from {p_name}'s perspective."
  plan_note = ChatGPT_single_request(plan_prompt)
  # print (plan_note)

  thought_prompt = statements + "\n"
  thought_prompt += f"Given the statements above, how might we summarize {p_name}'s feelings about their days up to now?\n\n"
  thought_prompt += f"Write the response from {p_name}'s perspective."
  thought_note = ChatGPT_single_request(thought_prompt)
  # print (thought_note)

  currently_prompt = f"{p_name}'s status from {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"
  currently_prompt += f"{persona.scratch.currently}\n\n"
  currently_prompt += f"{p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n" 
  currently_prompt += (plan_note + thought_note).replace('\n', '') + "\n\n"
  currently_prompt += f"It is now {persona.scratch.curr_time.strftime('%A %B %d')}. Given the above, write {p_name}'s status for {persona.scratch.curr_time.strftime('%A %B %d')} that reflects {p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}. Write this in third-person talking about {p_name}."
  currently_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement).\n\n"
  currently_prompt += "Follow this format below:\nStatus: <new status>"
  # print ("DEBUG ;adjhfno;asdjao;asdfsidfjo;af", p_name)
  # print (currently_prompt)
  new_currently = ChatGPT_single_request(currently_prompt)
  # print (new_currently)
  # print (new_currently[10:])

  persona.scratch.currently = new_currently
  reconcile_currently_with_employment_state(persona)

  daily_req_prompt = persona.scratch.get_str_iss() + "\n"
  daily_req_prompt += f"Today is {persona.scratch.curr_time.strftime('%A %B %d')}. Here is {persona.scratch.name}'s plan today in broad-strokes (with the time of the day. e.g., have a lunch at 12:00 pm, watch TV from 7 to 8 pm).\n\n"
  daily_req_prompt += f"Follow this format (the list should have 4~6 items but no more):\n"
  daily_req_prompt += f"1. wake up and complete the morning routine at <time>, 2. ..."

  new_daily_req = ChatGPT_single_request(daily_req_prompt)
  new_daily_req = new_daily_req.replace('\n', ' ')
  print ("WE ARE HERE!!!", new_daily_req)
  persona.scratch.daily_plan_req = new_daily_req


def _long_term_planning(persona, new_day): 
  """
  Formulates the persona's daily long-term plan if it is the start of a new 
  day. This basically has two components: first, we create the wake-up hour, 
  and second, we create the hourly schedule based on it. 
  INPUT
    new_day: Indicates whether the current time signals a "First day",
             "New day", or False (for neither). This is important because we
             create the personas' long term planning on the new day. 
  """
  # We start by creating the wake up hour for the persona. 
  wake_up_hour = generate_wake_up_hour(persona)

  # When it is a new day, we start by creating the daily_req of the persona.
  # Note that the daily_req is a list of strings that describe the persona's
  # day in broad strokes.
  if new_day == "First day": 
    # Bootstrapping the daily plan for the start of then generation:
    # if this is the start of generation (so there is no previous day's 
    # daily requirement, or if we are on a new day, we want to create a new
    # set of daily requirements.
    persona.scratch.daily_req = generate_first_daily_plan(persona, 
                                                          wake_up_hour)
  elif new_day == "New day":
    # Run all due surveys before revising identity / planning the new day.
    sim_code_file = os.path.join(fs_temp_storage, "curr_sim_code.json")
    with open(sim_code_file) as f:
      sim_code = json.load(f)["sim_code"]
    _run_surveys(persona, sim_code)
    revise_identity(persona)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - TODO
    # We need to create a new daily_req here...
    persona.scratch.daily_req = persona.scratch.daily_req

  # Based on the daily_req, we create an hourly schedule for the persona, 
  # which is a list of todo items with a time duration (in minutes) that 
  # add up to 24 hours.
  persona.scratch.f_daily_schedule = generate_hourly_schedule(persona, 
                                                              wake_up_hour)
  persona.scratch.f_daily_schedule_hourly_org = (persona.scratch
                                                   .f_daily_schedule[:])


  # Added March 4 -- adding plan to the memory.
  thought = f"This is {persona.scratch.name}'s plan for {persona.scratch.curr_time.strftime('%A %B %d')}:"
  for i in persona.scratch.daily_req: 
    thought += f" {i},"
  thought = thought[:-1] + "."
  created = persona.scratch.curr_time
  expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
  s, p, o = (persona.scratch.name, "plan", persona.scratch.curr_time.strftime('%A %B %d'))
  keywords = set(["plan"])
  thought_poignancy = 5
  thought_embedding_pair = (thought, get_embedding(thought))
  persona.a_mem.add_thought(created, expiration, s, p, o, 
                            thought, keywords, thought_poignancy, 
                            thought_embedding_pair, None)

  # print("Sleeping for 20 seconds...")
  # time.sleep(10)
  # print("Done sleeping!")



def _determine_action(persona, maze): 
  """
  Creates the next action sequence for the persona. 
  The main goal of this function is to run "add_new_action" on the persona's 
  scratch space, which sets up all the action related variables for the next 
  action. 
  As a part of this, the persona may need to decompose its hourly schedule as 
  needed.   
  INPUT
    persona: Current <Persona> instance whose action we are determining. 
    maze: Current <Maze> instance. 
  """
  def determine_decomp(act_desp, act_dura):
    """
    Given an action description and its duration, we determine whether we need
    to decompose it. If the action is about the agent sleeping, we generally
    do not want to decompose it, so that's what we catch here. 

    INPUT: 
      act_desp: the description of the action (e.g., "sleeping")
      act_dura: the duration of the action in minutes. 
    OUTPUT: 
      a boolean. True if we need to decompose, False otherwise. 
    """
    if "sleep" not in act_desp and "bed" not in act_desp: 
      return True
    elif "sleeping" in act_desp or "asleep" in act_desp or "in bed" in act_desp:
      return False
    elif "sleep" in act_desp or "bed" in act_desp: 
      if act_dura > 60: 
        return False
    return True

  # The goal of this function is to get us the action associated with 
  # <curr_index>. As a part of this, we may need to decompose some large 
  # chunk actions. 
  # Importantly, we try to decompose at least two hours worth of schedule at
  # any given point. 
  curr_index = persona.scratch.get_f_daily_schedule_index()
  curr_index_60 = persona.scratch.get_f_daily_schedule_index(advance=60)

  # * Decompose * 
  # During the first hour of the day, we need to decompose two hours 
  # sequence. We do that here. 
  if curr_index == 0:
    # This portion is invoked if it is the first hour of the day. 
    act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]
    if act_dura >= 60: 
      # We decompose if the next action is longer than an hour, and fits the
      # criteria described in determine_decomp.
      if determine_decomp(act_desp, act_dura): 
        persona.scratch.f_daily_schedule[curr_index:curr_index+1] = (
                            generate_task_decomp(persona, act_desp, act_dura))
    if curr_index_60 + 1 < len(persona.scratch.f_daily_schedule):
      act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60+1]
      if act_dura >= 60: 
        if determine_decomp(act_desp, act_dura): 
          persona.scratch.f_daily_schedule[curr_index_60+1:curr_index_60+2] = (
                            generate_task_decomp(persona, act_desp, act_dura))

  if curr_index_60 < len(persona.scratch.f_daily_schedule):
    # If it is not the first hour of the day, this is always invoked (it is
    # also invoked during the first hour of the day -- to double up so we can
    # decompose two hours in one go). Of course, we need to have something to
    # decompose as well, so we check for that too. 
    if persona.scratch.curr_time.hour < 23:
      # And we don't want to decompose after 11 pm. 
      act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60]
      if act_dura >= 60: 
        if determine_decomp(act_desp, act_dura): 
          persona.scratch.f_daily_schedule[curr_index_60:curr_index_60+1] = (
                              generate_task_decomp(persona, act_desp, act_dura))
  # * End of Decompose * 

  # Generate an <Action> instance from the action description and duration. By
  # this point, we assume that all the relevant actions are decomposed and 
  # ready in f_daily_schedule. 
  print ("DEBUG LJSDLFSKJF")
  for i in persona.scratch.f_daily_schedule: print (i)
  print (curr_index)
  print (len(persona.scratch.f_daily_schedule))
  print (persona.scratch.name)
  print ("------")

  # 1440
  x_emergency = 0
  for i in persona.scratch.f_daily_schedule: 
    x_emergency += i[1]
  # print ("x_emergency", x_emergency)

  if 1440 - x_emergency > 0: 
    print ("x_emergency__AAA", x_emergency)
  persona.scratch.f_daily_schedule += [["sleeping", 1440 - x_emergency]]
  



  act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index] 



  # Finding the target location of the action and creating action-related
  # variables.
  act_world = maze.access_tile(persona.scratch.curr_tile)["world"]
  # act_sector = maze.access_tile(persona.scratch.curr_tile)["sector"]
  act_sector = generate_action_sector(act_desp, persona, maze)
  act_arena = generate_action_arena(act_desp, persona, maze, act_world, act_sector)
  act_address = f"{act_world}:{act_sector}:{act_arena}"
  act_game_object = generate_action_game_object(act_desp, act_address,
                                                persona, maze)
  new_address = f"{act_world}:{act_sector}:{act_arena}:{act_game_object}"
  act_pron = generate_action_pronunciatio(act_desp, persona)
  act_event = generate_action_event_triple(act_desp, persona)
  # Persona's actions also influence the object states. We set those up here. 
  act_obj_desp = generate_act_obj_desc(act_game_object, act_desp, persona)
  act_obj_pron = generate_action_pronunciatio(act_obj_desp, persona)
  act_obj_event = generate_act_obj_event_triple(act_game_object, 
                                                act_obj_desp, persona)

  # Adding the action to persona's queue. 
  persona.scratch.add_new_action(new_address, 
                                 int(act_dura), 
                                 act_desp, 
                                 act_pron, 
                                 act_event,
                                 None,
                                 None,
                                 None,
                                 None,
                                 act_obj_desp, 
                                 act_obj_pron, 
                                 act_obj_event)


def _choose_retrieved(persona, retrieved): 
  """
  Retrieved elements have multiple core "curr_events". We need to choose one
  event to which we are going to react to. We pick that event here. 
  INPUT
    persona: Current <Persona> instance whose action we are determining. 
    retrieved: A dictionary of <ConceptNode> that were retrieved from the 
               the persona's associative memory. This dictionary takes the
               following form: 
               dictionary[event.description] = 
                 {["curr_event"] = <ConceptNode>, 
                  ["events"] = [<ConceptNode>, ...], 
                  ["thoughts"] = [<ConceptNode>, ...] }
  """
  # Once we are done with the reflection, we might want to build a more  
  # complex structure here.
  
  # We do not want to take self events... for now 
  copy_retrieved = retrieved.copy()
  for event_desc, rel_ctx in copy_retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if curr_event.subject == persona.name: 
      del retrieved[event_desc]

  # Always choose persona first.
  priority = []
  for event_desc, rel_ctx in retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if (":" not in curr_event.subject 
        and curr_event.subject != persona.name): 
      priority += [rel_ctx]
  if priority: 
    return random.choice(priority)

  # Skip idle. 
  for event_desc, rel_ctx in retrieved.items(): 
    curr_event = rel_ctx["curr_event"]
    if "is idle" not in event_desc: 
      priority += [rel_ctx]
  if priority: 
    return random.choice(priority)
  return None


def _should_react(persona, retrieved, personas): 
  """
  Determines what form of reaction the persona should exihibit given the 
  retrieved values. 
  INPUT
    persona: Current <Persona> instance whose action we are determining. 
    retrieved: A dictionary of <ConceptNode> that were retrieved from the 
               the persona's associative memory. This dictionary takes the
               following form: 
               dictionary[event.description] = 
                 {["curr_event"] = <ConceptNode>, 
                  ["events"] = [<ConceptNode>, ...], 
                  ["thoughts"] = [<ConceptNode>, ...] }
    personas: A dictionary that contains all persona names as keys, and the 
              <Persona> instance as values. 
  """
  def lets_talk(init_persona, target_persona, retrieved):
    if (not target_persona.scratch.act_address 
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description): 
      return False

    if ("sleeping" in target_persona.scratch.act_description 
        or "sleeping" in init_persona.scratch.act_description): 
      return False

    if init_persona.scratch.curr_time.hour == 23: 
      return False

    if "<waiting>" in target_persona.scratch.act_address: 
      return False

    if (target_persona.scratch.chatting_with 
      or init_persona.scratch.chatting_with): 
      return False

    if (target_persona.name in init_persona.scratch.chatting_with_buffer): 
      if init_persona.scratch.chatting_with_buffer[target_persona.name] > 0: 
        return False

    if generate_decide_to_talk(init_persona, target_persona, retrieved): 

      return True

    return False

  def lets_react(init_persona, target_persona, retrieved): 
    if (not target_persona.scratch.act_address 
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description): 
      return False

    if ("sleeping" in target_persona.scratch.act_description 
        or "sleeping" in init_persona.scratch.act_description): 
      return False

    # return False
    if init_persona.scratch.curr_time.hour == 23: 
      return False

    if "waiting" in target_persona.scratch.act_description: 
      return False
    if init_persona.scratch.planned_path == []:
      return False

    if (init_persona.scratch.act_address 
        != target_persona.scratch.act_address): 
      return False

    react_mode = generate_decide_to_react(init_persona, 
                                          target_persona, retrieved)

    if react_mode == "1": 
      wait_until = ((target_persona.scratch.act_start_time 
        + datetime.timedelta(minutes=target_persona.scratch.act_duration - 1))
        .strftime("%B %d, %Y, %H:%M:%S"))
      return f"wait: {wait_until}"
    elif react_mode == "2":
      return False
      return "do other things"
    else:
      return False #"keep" 

  # If the persona is chatting right now, default to no reaction 
  if persona.scratch.chatting_with: 
    return False
  if "<waiting>" in persona.scratch.act_address: 
    return False

  # Recall that retrieved takes the following form: 
  # dictionary {["curr_event"] = <ConceptNode>, 
  #             ["events"] = [<ConceptNode>, ...], 
  #             ["thoughts"] = [<ConceptNode>, ...]}
  curr_event = retrieved["curr_event"]

  if ":" not in curr_event.subject: 
    # this is a persona event. 
    if lets_talk(persona, personas[curr_event.subject], retrieved):
      return f"chat with {curr_event.subject}"
    react_mode = lets_react(persona, personas[curr_event.subject], 
                            retrieved)
    return react_mode
  return False


def _create_react(persona, inserted_act, inserted_act_dur,
                  act_address, act_event, chatting_with, chat, chatting_with_buffer,
                  chatting_end_time, 
                  act_pronunciatio, act_obj_description, act_obj_pronunciatio, 
                  act_obj_event, act_start_time=None): 
  p = persona 

  min_sum = 0
  for i in range (p.scratch.get_f_daily_schedule_hourly_org_index()): 
    min_sum += p.scratch.f_daily_schedule_hourly_org[i][1]
  start_hour = int (min_sum/60)

  if (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] >= 120):
    end_hour = start_hour + p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1]/60

  elif (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] + 
      p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()+1][1]): 
    end_hour = start_hour + ((p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] + 
              p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()+1][1])/60)

  else: 
    end_hour = start_hour + 2
  end_hour = int(end_hour)

  dur_sum = 0
  count = 0 
  start_index = None
  end_index = None
  for act, dur in p.scratch.f_daily_schedule: 
    if dur_sum >= start_hour * 60 and start_index == None:
      start_index = count
    if dur_sum >= end_hour * 60 and end_index == None: 
      end_index = count
    dur_sum += dur
    count += 1

  ret = generate_new_decomp_schedule(p, inserted_act, inserted_act_dur, 
                                       start_hour, end_hour)
  p.scratch.f_daily_schedule[start_index:end_index] = ret
  p.scratch.add_new_action(act_address,
                           inserted_act_dur,
                           inserted_act,
                           act_pronunciatio,
                           act_event,
                           chatting_with,
                           chat,
                           chatting_with_buffer,
                           chatting_end_time,
                           act_obj_description,
                           act_obj_pronunciatio,
                           act_obj_event,
                           act_start_time)


def _chat_react(maze, persona, focused_event, reaction_mode, personas):
  # There are two personas -- the persona who is initiating the conversation
  # and the persona who is the target. We get the persona instances here. 
  init_persona = persona
  target_persona = personas[reaction_mode[9:].strip()]
  curr_personas = [init_persona, target_persona]

  # Actually creating the conversation here. 
  convo, duration_min = generate_convo(maze, init_persona, target_persona)
  convo_summary = generate_convo_summary(init_persona, convo)
  inserted_act = convo_summary
  inserted_act_dur = duration_min

  act_start_time = target_persona.scratch.act_start_time

  curr_time = target_persona.scratch.curr_time
  if curr_time.second != 0: 
    temp_curr_time = curr_time + datetime.timedelta(seconds=60 - curr_time.second)
    chatting_end_time = temp_curr_time + datetime.timedelta(minutes=inserted_act_dur)
  else: 
    chatting_end_time = curr_time + datetime.timedelta(minutes=inserted_act_dur)

  for role, p in [("init", init_persona), ("target", target_persona)]: 
    if role == "init": 
      act_address = f"<persona> {target_persona.name}"
      act_event = (p.name, "chat with", target_persona.name)
      chatting_with = target_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[target_persona.name] = 800
    elif role == "target": 
      act_address = f"<persona> {init_persona.name}"
      act_event = (p.name, "chat with", init_persona.name)
      chatting_with = init_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[init_persona.name] = 800

    act_pronunciatio = "💬" 
    act_obj_description = None
    act_obj_pronunciatio = None
    act_obj_event = (None, None, None)

    _create_react(p, inserted_act, inserted_act_dur,
      act_address, act_event, chatting_with, convo, chatting_with_buffer, chatting_end_time,
      act_pronunciatio, act_obj_description, act_obj_pronunciatio, 
      act_obj_event, act_start_time)


def _wait_react(persona, reaction_mode): 
  p = persona

  inserted_act = f'waiting to start {p.scratch.act_description.split("(")[-1][:-1]}'
  end_time = datetime.datetime.strptime(reaction_mode[6:].strip(), "%B %d, %Y, %H:%M:%S")
  inserted_act_dur = (end_time.minute + end_time.hour * 60) - (p.scratch.curr_time.minute + p.scratch.curr_time.hour * 60) + 1

  act_address = f"<waiting> {p.scratch.curr_tile[0]} {p.scratch.curr_tile[1]}"
  act_event = (p.name, "waiting to start", p.scratch.act_description.split("(")[-1][:-1])
  chatting_with = None
  chat = None
  chatting_with_buffer = None
  chatting_end_time = None

  act_pronunciatio = "⌛" 
  act_obj_description = None
  act_obj_pronunciatio = None
  act_obj_event = (None, None, None)

  _create_react(p, inserted_act, inserted_act_dur,
    act_address, act_event, chatting_with, chat, chatting_with_buffer, chatting_end_time,
    act_pronunciatio, act_obj_description, act_obj_pronunciatio, act_obj_event)


def plan(persona, maze, personas, new_day, retrieved): 
  """
  Main cognitive function of the chain. It takes the retrieved memory and 
  perception, as well as the maze and the first day state to conduct both 
  the long term and short term planning for the persona. 

  INPUT: 
    maze: Current <Maze> instance of the world. 
    personas: A dictionary that contains all persona names as keys, and the 
              Persona instance as values. 
    new_day: This can take one of the three values. 
      1) <Boolean> False -- It is not a "new day" cycle (if it is, we would
         need to call the long term planning sequence for the persona). 
      2) <String> "First day" -- It is literally the start of a simulation,
         so not only is it a new day, but also it is the first day. 
      2) <String> "New day" -- It is a new day. 
    retrieved: dictionary of dictionary. The first layer specifies an event,
               while the latter layer specifies the "curr_event", "events", 
               and "thoughts" that are relevant.
  OUTPUT 
    The target action address of the persona (persona.scratch.act_address).
  """ 
  # PART 1: Generate the hourly schedule. 
  if new_day: 
    _long_term_planning(persona, new_day)

  # PART 2: If the current action has expired, we want to create a new plan.
  if persona.scratch.act_check_finished(): 
    _determine_action(persona, maze)

  # PART 3: If you perceived an event that needs to be responded to (saw 
  # another persona), and retrieved relevant information. 
  # Step 1: Retrieved may have multiple events represented in it. The first 
  #         job here is to determine which of the events we want to focus 
  #         on for the persona. 
  #         <focused_event> takes the form of a dictionary like this: 
  #         dictionary {["curr_event"] = <ConceptNode>, 
  #                     ["events"] = [<ConceptNode>, ...], 
  #                     ["thoughts"] = [<ConceptNode>, ...]}
  focused_event = False
  if retrieved.keys(): 
    focused_event = _choose_retrieved(persona, retrieved)
  
  # Step 2: Once we choose an event, we need to determine whether the
  #         persona will take any actions for the perceived event. There are
  #         three possible modes of reaction returned by _should_react. 
  #         a) "chat with {target_persona.name}"
  #         b) "react"
  #         c) False
  if focused_event: 
    reaction_mode = _should_react(persona, focused_event, personas)
    if reaction_mode: 
      # If we do want to chat, then we generate conversation 
      if reaction_mode[:9] == "chat with":
        _chat_react(maze, persona, focused_event, reaction_mode, personas)
      elif reaction_mode[:4] == "wait": 
        _wait_react(persona, reaction_mode)
      # elif reaction_mode == "do other things": 
      #   _chat_react(persona, focused_event, reaction_mode, personas)

  # Step 3: Chat-related state clean up. 
  # If the persona is not chatting with anyone, we clean up any of the 
  # chat-related states here. 
  if persona.scratch.act_event[1] != "chat with":
    persona.scratch.chatting_with = None
    persona.scratch.chat = None
    persona.scratch.chatting_end_time = None
  # We want to make sure that the persona does not keep conversing with each
  # other in an infinite loop. So, chatting_with_buffer maintains a form of 
  # buffer that makes the persona wait from talking to the same target 
  # immediately after chatting once. We keep track of the buffer value here. 
  curr_persona_chat_buffer = persona.scratch.chatting_with_buffer
  for persona_name, buffer_count in curr_persona_chat_buffer.items():
    if persona_name != persona.scratch.chatting_with: 
      persona.scratch.chatting_with_buffer[persona_name] -= 1

  return persona.scratch.act_address













































 
