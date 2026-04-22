"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: scratch.py
Description: Defines the short-term memory module for generative agents.
"""
import datetime
import json
import os
import sys
sys.path.append('../../')

from global_methods import *

class Scratch: 
  def __init__(self, f_saved): 
    # PERSONA HYPERPARAMETERS
    # <vision_r> denotes the number of tiles that the persona can see around 
    # them. 
    self.vision_r = 4
    # <att_bandwidth> TODO 
    self.att_bandwidth = 3
    # <retention> TODO 
    self.retention = 5

    # WORLD INFORMATION
    # Perceived world time. 
    self.curr_time = None
    # Current x,y tile coordinate of the persona. 
    self.curr_tile = None
    # Perceived world daily requirement. 
    self.daily_plan_req = None
    
    # THE CORE IDENTITY OF THE PERSONA 
    # Base information about the persona.
    self.name = None
    self.first_name = None
    self.last_name = None
    self.age = None
    # L0 permanent core traits.  
    self.innate = None
    # L1 stable traits.
    self.learned = None
    # L2 external implementation. 
    self.currently = None
    self.lifestyle = None
    self.living_area = None

    # Employment data is persisted outside scratch.json.
    # We keep only caches here and derive the current profile from:
    # 1) a persisted baseline inferred from the original persona text
    # 2) a persisted employment event log
    scratch_path = os.path.abspath(f_saved) if f_saved else None
    self._persona_dir = (os.path.dirname(os.path.dirname(scratch_path))
                         if scratch_path else None)
    self._employment_baseline_cache = None
    self._employment_events_cache = None
    # REFLECTION VARIABLES
    self.concept_forget = 100
    self.daily_reflection_time = 60 * 3
    self.daily_reflection_size = 5
    self.overlap_reflect_th = 2
    self.kw_strg_event_reflect_th = 4
    self.kw_strg_thought_reflect_th = 4

    # New reflection variables
    self.recency_w = 1
    self.relevance_w = 1
    self.importance_w = 1
    self.recency_decay = 0.99
    self.importance_trigger_max = 150
    self.importance_trigger_curr = self.importance_trigger_max
    self.importance_ele_n = 0 
    self.thought_count = 5

    # PERSONA PLANNING 
    # <daily_req> is a list of various goals the persona is aiming to achieve
    # today. 
    # e.g., ['Work on her paintings for her upcoming show', 
    #        'Take a break to watch some TV', 
    #        'Make lunch for herself', 
    #        'Work on her paintings some more', 
    #        'Go to bed early']
    # They have to be renewed at the end of the day, which is why we are
    # keeping track of when they were first generated. 
    self.daily_req = []
    # <f_daily_schedule> denotes a form of long term planning. This lays out 
    # the persona's daily plan. 
    # Note that we take the long term planning and short term decomposition 
    # appoach, which is to say that we first layout hourly schedules and 
    # gradually decompose as we go. 
    # Three things to note in the example below: 
    # 1) See how "sleeping" was not decomposed -- some of the common events 
    #    really, just mainly sleeping, are hard coded to be not decomposable.
    # 2) Some of the elements are starting to be decomposed... More of the 
    #    things will be decomposed as the day goes on (when they are 
    #    decomposed, they leave behind the original hourly action description
    #    in tact).
    # 3) The latter elements are not decomposed. When an event occurs, the
    #    non-decomposed elements go out the window.  
    # e.g., [['sleeping', 360], 
    #         ['wakes up and ... (wakes up and stretches ...)', 5], 
    #         ['wakes up and starts her morning routine (out of bed )', 10],
    #         ...
    #         ['having lunch', 60], 
    #         ['working on her painting', 180], ...]
    self.f_daily_schedule = []
    # <f_daily_schedule_hourly_org> is a replica of f_daily_schedule
    # initially, but retains the original non-decomposed version of the hourly
    # schedule. 
    # e.g., [['sleeping', 360], 
    #        ['wakes up and starts her morning routine', 120],
    #        ['working on her painting', 240], ... ['going to bed', 60]]
    self.f_daily_schedule_hourly_org = []
    
    # CURR ACTION 
    # <address> is literally the string address of where the action is taking 
    # place.  It comes in the form of 
    # "{world}:{sector}:{arena}:{game_objects}". It is important that you 
    # access this without doing negative indexing (e.g., [-1]) because the 
    # latter address elements may not be present in some cases. 
    # e.g., "dolores double studio:double studio:bedroom 1:bed"
    self.act_address = None
    # <start_time> is a python datetime instance that indicates when the 
    # action has started. 
    self.act_start_time = None
    # <duration> is the integer value that indicates the number of minutes an
    # action is meant to last. 
    self.act_duration = None
    # <description> is a string description of the action. 
    self.act_description = None
    # <pronunciatio> is the descriptive expression of the self.description. 
    # Currently, it is implemented as emojis. 
    self.act_pronunciatio = None
    # <event_form> represents the event triple that the persona is currently 
    # engaged in. 
    self.act_event = (self.name, None, None)

    # <obj_description> is a string description of the object action. 
    self.act_obj_description = None
    # <obj_pronunciatio> is the descriptive expression of the object action. 
    # Currently, it is implemented as emojis. 
    self.act_obj_pronunciatio = None
    # <obj_event_form> represents the event triple that the action object is  
    # currently engaged in. 
    self.act_obj_event = (self.name, None, None)

    # <chatting_with> is the string name of the persona that the current 
    # persona is chatting with. None if it does not exist. 
    self.chatting_with = None
    # <chat> is a list of list that saves a conversation between two personas.
    # It comes in the form of: [["Dolores Murphy", "Hi"], 
    #                           ["Maeve Jenson", "Hi"] ...]
    self.chat = None
    # <chatting_with_buffer>  
    # e.g., ["Dolores Murphy"] = self.vision_r
    self.chatting_with_buffer = dict()
    self.chatting_end_time = None

    # <path_set> is True if we've already calculated the path the persona will
    # take to execute this action. That path is stored in the persona's 
    # scratch.planned_path.
    self.act_path_set = False
    # <planned_path> is a list of x y coordinate tuples (tiles) that describe
    # the path the persona is to take to execute the <curr_action>. 
    # The list does not include the persona's current tile, and includes the 
    # destination tile. 
    # e.g., [(50, 10), (49, 10), (48, 10), ...]
    self.planned_path = []

    if check_if_file_exists(f_saved): 
      # If we have a bootstrap file, load that here. 
      scratch_load = json.load(open(f_saved))

      self.vision_r = scratch_load["vision_r"]
      self.att_bandwidth = scratch_load["att_bandwidth"]
      self.retention = scratch_load["retention"]

      if scratch_load["curr_time"]: 
        self.curr_time = datetime.datetime.strptime(scratch_load["curr_time"],
                                                  "%B %d, %Y, %H:%M:%S")
      else: 
        self.curr_time = None
      self.curr_tile = scratch_load["curr_tile"]
      self.daily_plan_req = scratch_load["daily_plan_req"]

      self.name = scratch_load["name"]
      self.first_name = scratch_load["first_name"]
      self.last_name = scratch_load["last_name"]
      self.age = scratch_load["age"]
      self.innate = scratch_load["innate"]
      self.learned = scratch_load["learned"]
      self.currently = scratch_load["currently"]
      self.lifestyle = scratch_load["lifestyle"]
      self.living_area = scratch_load["living_area"]

      self.concept_forget = scratch_load["concept_forget"]
      self.daily_reflection_time = scratch_load["daily_reflection_time"]
      self.daily_reflection_size = scratch_load["daily_reflection_size"]
      self.overlap_reflect_th = scratch_load["overlap_reflect_th"]
      self.kw_strg_event_reflect_th = scratch_load["kw_strg_event_reflect_th"]
      self.kw_strg_thought_reflect_th = scratch_load["kw_strg_thought_reflect_th"]

      self.recency_w = scratch_load["recency_w"]
      self.relevance_w = scratch_load["relevance_w"]
      self.importance_w = scratch_load["importance_w"]
      self.recency_decay = scratch_load["recency_decay"]
      self.importance_trigger_max = scratch_load["importance_trigger_max"]
      self.importance_trigger_curr = scratch_load["importance_trigger_curr"]
      self.importance_ele_n = scratch_load["importance_ele_n"]
      self.thought_count = scratch_load["thought_count"]

      self.daily_req = scratch_load["daily_req"]
      self.f_daily_schedule = scratch_load["f_daily_schedule"]
      self.f_daily_schedule_hourly_org = scratch_load["f_daily_schedule_hourly_org"]

      self.act_address = scratch_load["act_address"]
      if scratch_load["act_start_time"]: 
        self.act_start_time = datetime.datetime.strptime(
                                              scratch_load["act_start_time"],
                                              "%B %d, %Y, %H:%M:%S")
      else: 
        self.curr_time = None
      self.act_duration = scratch_load["act_duration"]
      self.act_description = scratch_load["act_description"]
      self.act_pronunciatio = scratch_load["act_pronunciatio"]
      self.act_event = tuple(scratch_load["act_event"])

      self.act_obj_description = scratch_load["act_obj_description"]
      self.act_obj_pronunciatio = scratch_load["act_obj_pronunciatio"]
      self.act_obj_event = tuple(scratch_load["act_obj_event"])

      self.chatting_with = scratch_load["chatting_with"]
      self.chat = scratch_load["chat"]
      self.chatting_with_buffer = scratch_load["chatting_with_buffer"]
      if scratch_load["chatting_end_time"]: 
        self.chatting_end_time = datetime.datetime.strptime(
                                            scratch_load["chatting_end_time"],
                                            "%B %d, %Y, %H:%M:%S")
      else:
        self.chatting_end_time = None

      self.act_path_set = scratch_load["act_path_set"]
      self.planned_path = scratch_load["planned_path"]


  def save(self, out_json):
    """
    Save persona's scratch. 

    INPUT: 
      out_json: The file where we wil be saving our persona's state. 
    OUTPUT: 
      None
    """
    scratch = dict() 
    scratch["vision_r"] = self.vision_r
    scratch["att_bandwidth"] = self.att_bandwidth
    scratch["retention"] = self.retention

    scratch["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
    scratch["curr_tile"] = self.curr_tile
    scratch["daily_plan_req"] = self.daily_plan_req

    scratch["name"] = self.name
    scratch["first_name"] = self.first_name
    scratch["last_name"] = self.last_name
    scratch["age"] = self.age
    scratch["innate"] = self.innate
    scratch["learned"] = self.learned
    scratch["currently"] = self.currently
    scratch["lifestyle"] = self.lifestyle
    scratch["living_area"] = self.living_area
    scratch["concept_forget"] = self.concept_forget
    scratch["daily_reflection_time"] = self.daily_reflection_time
    scratch["daily_reflection_size"] = self.daily_reflection_size
    scratch["overlap_reflect_th"] = self.overlap_reflect_th
    scratch["kw_strg_event_reflect_th"] = self.kw_strg_event_reflect_th
    scratch["kw_strg_thought_reflect_th"] = self.kw_strg_thought_reflect_th

    scratch["recency_w"] = self.recency_w
    scratch["relevance_w"] = self.relevance_w
    scratch["importance_w"] = self.importance_w
    scratch["recency_decay"] = self.recency_decay
    scratch["importance_trigger_max"] = self.importance_trigger_max
    scratch["importance_trigger_curr"] = self.importance_trigger_curr
    scratch["importance_ele_n"] = self.importance_ele_n
    scratch["thought_count"] = self.thought_count

    scratch["daily_req"] = self.daily_req
    scratch["f_daily_schedule"] = self.f_daily_schedule
    scratch["f_daily_schedule_hourly_org"] = self.f_daily_schedule_hourly_org

    scratch["act_address"] = self.act_address
    scratch["act_start_time"] = (self.act_start_time
                                     .strftime("%B %d, %Y, %H:%M:%S"))
    scratch["act_duration"] = self.act_duration
    scratch["act_description"] = self.act_description
    scratch["act_pronunciatio"] = self.act_pronunciatio
    scratch["act_event"] = self.act_event

    scratch["act_obj_description"] = self.act_obj_description
    scratch["act_obj_pronunciatio"] = self.act_obj_pronunciatio
    scratch["act_obj_event"] = self.act_obj_event

    scratch["chatting_with"] = self.chatting_with
    scratch["chat"] = self.chat
    scratch["chatting_with_buffer"] = self.chatting_with_buffer
    if self.chatting_end_time: 
      scratch["chatting_end_time"] = (self.chatting_end_time
                                        .strftime("%B %d, %Y, %H:%M:%S"))
    else: 
      scratch["chatting_end_time"] = None

    scratch["act_path_set"] = self.act_path_set
    scratch["planned_path"] = self.planned_path

    with open(out_json, "w") as outfile:
      json.dump(scratch, outfile, indent=2) 


  def get_f_daily_schedule_index(self, advance=0):
    """
    We get the current index of self.f_daily_schedule. 

    Recall that self.f_daily_schedule stores the decomposed action sequences 
    up until now, and the hourly sequences of the future action for the rest
    of today. Given that self.f_daily_schedule is a list of list where the 
    inner list is composed of [task, duration], we continue to add up the 
    duration until we reach "if elapsed > today_min_elapsed" condition. The
    index where we stop is the index we will return. 

    INPUT
      advance: Integer value of the number minutes we want to look into the 
               future. This allows us to get the index of a future timeframe.
    OUTPUT 
      an integer value for the current index of f_daily_schedule.
    """
    # We first calculate teh number of minutes elapsed today. 
    today_min_elapsed = 0
    today_min_elapsed += self.curr_time.hour * 60
    today_min_elapsed += self.curr_time.minute
    today_min_elapsed += advance

    x = 0
    for task, duration in self.f_daily_schedule: 
      x += duration
    x = 0
    for task, duration in self.f_daily_schedule_hourly_org: 
      x += duration

    # We then calculate the current index based on that. 
    curr_index = 0
    elapsed = 0
    for task, duration in self.f_daily_schedule: 
      elapsed += duration
      if elapsed > today_min_elapsed: 
        return curr_index
      curr_index += 1

    return curr_index


  def get_f_daily_schedule_hourly_org_index(self, advance=0):
    """
    We get the current index of self.f_daily_schedule_hourly_org. 
    It is otherwise the same as get_f_daily_schedule_index. 

    INPUT
      advance: Integer value of the number minutes we want to look into the 
               future. This allows us to get the index of a future timeframe.
    OUTPUT 
      an integer value for the current index of f_daily_schedule.
    """
    # We first calculate teh number of minutes elapsed today. 
    today_min_elapsed = 0
    today_min_elapsed += self.curr_time.hour * 60
    today_min_elapsed += self.curr_time.minute
    today_min_elapsed += advance
    # We then calculate the current index based on that. 
    curr_index = 0
    elapsed = 0
    for task, duration in self.f_daily_schedule_hourly_org: 
      elapsed += duration
      if elapsed > today_min_elapsed: 
        return curr_index
      curr_index += 1
    return curr_index


  def get_str_iss(self): 
    """
    ISS stands for "identity stable set." This describes the commonset summary
    of this persona -- basically, the bare minimum description of the persona
    that gets used in almost all prompts that need to call on the persona. 

    INPUT
      None
    OUTPUT
      the identity stable set summary of the persona in a string form.
    EXAMPLE STR OUTPUT
      "Name: Dolores Heitmiller
       Age: 28
       Innate traits: hard-edged, independent, loyal
       Learned traits: Dolores is a painter who wants live quietly and paint 
         while enjoying her everyday life.
       Currently: Dolores is preparing for her first solo show. She mostly 
         works from home.
       Lifestyle: Dolores goes to bed around 11pm, sleeps for 7 hours, eats 
         dinner around 6pm.
       Daily plan requirement: Dolores is planning to stay at home all day and 
         never go out."
    """
    commonset = ""
    commonset += f"Name: {self.name}\n"
    commonset += f"Age: {self.age}\n"
    commonset += f"Innate traits: {self.innate}\n"
    commonset += f"Learned traits: {self.learned}\n"
    commonset += f"Currently: {self.currently}\n"
    commonset += f"Lifestyle: {self.lifestyle}\n"
    commonset += f"Employment: {self.get_str_employment_status()}\n"
    commonset += f"Daily plan requirement: {self.daily_plan_req}\n"
    commonset += f"Current Date: {self.curr_time.strftime('%A %B %d')}\n"
    return commonset


  def get_str_name(self): 
    return self.name


  def get_str_firstname(self): 
    return self.first_name


  def get_str_lastname(self): 
    return self.last_name


  def get_str_age(self): 
    return str(self.age)


  def get_str_innate(self): 
    return self.innate


  def get_str_learned(self): 
    return self.learned


  def get_str_currently(self): 
    return self.currently


  def get_str_lifestyle(self): 
    return self.lifestyle

  def _normalize_employment_value(self, value):
    """Treat placeholder model output as missing employment data."""
    if value is None:
      return None

    value = str(value).strip()
    if not value:
      return None

    if value.lower() in ["unknown", "unspecified", "none", "null", "n/a", "na"]:
      return None

    return value

  def _normalize_employment_profile(self, profile=None):
    """Normalize an employment profile dictionary into canonical values."""
    profile = profile or {}
    normalized = {
      "employment_status": self._normalize_employment_value(
          profile.get("employment_status")),
      "job_title": self._normalize_employment_value(profile.get("job_title")),
      "employer": self._normalize_employment_value(profile.get("employer")),
      "workplace": self._normalize_employment_value(profile.get("workplace")),
    }

    if (not normalized["employment_status"]
        and any(normalized[key] for key in ["job_title", "employer", "workplace"])):
      normalized["employment_status"] = "employed"

    return normalized

  def _get_employment_baseline_path(self):
    if not self._persona_dir:
      return None
    return os.path.join(self._persona_dir, "employment", "baseline_profile.json")

  def _get_employment_events_path(self):
    if not self._persona_dir:
      return None
    return os.path.join(self._persona_dir, "employment", "events.json")

  def _read_json_resource(self, path, default):
    if not path or not check_if_file_exists(path):
      return default

    try:
      with open(path, "r") as infile:
        return json.load(infile)
    except Exception:
      return default

  def _write_json_resource(self, path, payload):
    if not path:
      return False

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as outfile:
      json.dump(payload, outfile, indent=2)
    return True

  def get_employment_inference_source(self):
    """
    Return the baseline-employment prompt inputs derived from persona text.
    This is intentionally based on the original scratch fields, not any
    runtime-emergent employment state.
    """
    current_date = (self.curr_time.strftime('%A %B %d')
                    if self.curr_time else "Unknown")
    commonset = ""
    commonset += f"Name: {self.name}\n"
    commonset += f"Age: {self.age}\n"
    commonset += f"Innate traits: {self.innate}\n"
    commonset += f"Learned traits: {self.learned}\n"
    commonset += f"Currently: {self.currently}\n"
    commonset += f"Lifestyle: {self.lifestyle}\n"
    commonset += f"Daily plan requirement: {self.daily_plan_req}\n"
    commonset += f"Current Date: {current_date}\n"

    return [
      commonset,
      self.daily_plan_req or "unknown",
      self.learned or "unknown",
      self.currently or "unknown",
      self.lifestyle or "unknown",
    ]

  def get_employment_reconciliation_source(self):
    """
    Return prompt inputs for reconciling current employment state from the
    persona's updated narrative and recent planning context.
    """
    current_date = (self.curr_time.strftime('%A %B %d')
                    if self.curr_time else "Unknown")
    daily_context = (", ".join(self.daily_req)
                     if self.daily_req else self.daily_plan_req)
    schedule_context = ("; ".join(
      [f"{act} ({dur} min)" for act, dur in self.f_daily_schedule_hourly_org])
      if self.f_daily_schedule_hourly_org else "unknown")

    commonset = ""
    commonset += f"Name: {self.name}\n"
    commonset += f"Age: {self.age}\n"
    commonset += f"Innate traits: {self.innate}\n"
    commonset += f"Learned traits: {self.learned}\n"
    commonset += f"Currently: {self.currently}\n"
    commonset += f"Lifestyle: {self.lifestyle}\n"
    commonset += f"Daily plan requirement: {self.daily_plan_req}\n"
    commonset += f"Recent daily context: {daily_context or 'unknown'}\n"
    commonset += f"Recent schedule: {schedule_context}\n"
    commonset += f"Current Date: {current_date}\n"

    return [
      commonset,
      daily_context or "unknown",
      self.learned or "unknown",
      self.currently or "unknown",
      self.lifestyle or "unknown",
    ]

  def get_baseline_employment_profile(self):
    """Load the persisted baseline employment profile, if one exists."""
    if self._employment_baseline_cache is None:
      baseline = self._read_json_resource(self._get_employment_baseline_path(), {})
      self._employment_baseline_cache = self._normalize_employment_profile(
        baseline if isinstance(baseline, dict) else {})

    return dict(self._employment_baseline_cache)

  def has_persisted_employment_baseline(self):
    """Return True when a baseline employment profile has been persisted."""
    profile = self.get_baseline_employment_profile()
    return any(profile.values())

  def persist_employment_baseline(self, profile):
    """Persist a normalized baseline employment profile outside scratch.json."""
    normalized = self._normalize_employment_profile(profile)
    if not any(normalized.values()):
      return False

    self._employment_baseline_cache = normalized
    return self._write_json_resource(self._get_employment_baseline_path(),
                                     normalized)

  def get_employment_events(self):
    """Load the persisted employment event log."""
    if self._employment_events_cache is None:
      events = self._read_json_resource(self._get_employment_events_path(), [])
      self._employment_events_cache = events if isinstance(events, list) else []

    return list(self._employment_events_cache)

  def _apply_employment_event_to_profile(self, profile, event):
    """Apply one logged employment event onto an employment profile."""
    updated = dict(profile)
    normalized_type = str(event.get("event_type", "")).strip().lower()

    status = self._normalize_employment_value(
      event.get("status_after") or event.get("employment_status"))
    employer = self._normalize_employment_value(event.get("employer"))
    job_title = self._normalize_employment_value(event.get("job_title"))
    workplace = self._normalize_employment_value(event.get("workplace"))

    if normalized_type == "termination":
      updated["employment_status"] = status or "unemployed"
      updated["employer"] = None
      updated["job_title"] = None
      updated["workplace"] = None
      return updated

    if normalized_type in ["job_acquisition", "promotion", "transition"]:
      if normalized_type == "job_acquisition":
        updated["employment_status"] = status or "employed"
      elif normalized_type == "promotion":
        updated["employment_status"] = (status
                                         or updated.get("employment_status")
                                         or "employed")
      elif normalized_type == "transition":
        updated["employment_status"] = status or "employed"

      if employer is not None:
        updated["employer"] = employer
      if job_title is not None:
        updated["job_title"] = job_title
      if workplace is not None:
        updated["workplace"] = workplace
      return updated

    if status is not None:
      updated["employment_status"] = status
    if employer is not None:
      updated["employer"] = employer
    if job_title is not None:
      updated["job_title"] = job_title
    if workplace is not None:
      updated["workplace"] = workplace
    return updated

  def get_current_employment_profile(self):
    """
    Derive the agent's current employment profile from the persisted baseline
    plus all persisted employment events.
    """
    profile = self._normalize_employment_profile(
      self.get_baseline_employment_profile())

    for event in self.get_employment_events():
      if isinstance(event, dict):
        profile = self._apply_employment_event_to_profile(profile, event)

    return self._normalize_employment_profile(profile)

  def get_str_employment_status(self):
    """Return a descriptive employment summary for prompts and logs."""
    profile = self.get_current_employment_profile()
    status = profile["employment_status"]
    job_title = profile["job_title"]
    employer = profile["employer"]
    workplace = profile["workplace"]
    events = self.get_employment_events()

    if not any([status, job_title, employer, workplace, bool(events)]):
      return f"{self.first_name}'s employment situation is currently unspecified."

    if status == "student":
      description = f"{self.first_name} is currently a student"
    elif status == "caregiver":
      description = f"{self.first_name}'s primary role is caregiving"
    elif status == "informal_work":
      description = f"{self.first_name} is currently doing informal work"
    elif status:
      description = f"{self.first_name} is currently {status}"
    elif job_title or employer or workplace:
      description = f"{self.first_name} is currently employed"
    else:
      description = f"{self.first_name} has recent employment activity"

    if job_title:
      description += f" as {job_title}"
    if employer:
      description += f" at {employer}"
    if workplace and workplace != employer:
      description += f" in {workplace}"
    description += "."

    recent_events = self.get_recent_employment_events_str(limit=3, include_timestamp=False)
    if recent_events:
      description += f" Recent employment events: {recent_events}"
    return description

  def get_recent_employment_events_str(self, limit=5, include_timestamp=True):
    """Return a readable string of recent employment events."""
    events = self.get_employment_events()
    if not events:
      return ""

    recent_entries = events[-1 * max(1, limit):]
    parts = []
    for entry in recent_entries:
      if isinstance(entry, dict):
        timestamp = entry.get("timestamp")
        description = entry.get("description") or entry.get("event_type") or "employment update"
        if include_timestamp and timestamp:
          parts.append(f"[{timestamp}] {description}")
        else:
          parts.append(description)
      else:
        parts.append(str(entry))
    return "; ".join(parts)

  def log_employment_event(self, event_type, description, employer=None,
                           job_title=None, workplace=None,
                           employment_status=None,
                           metadata=None):
    """Persist a timestamped employment event outside scratch.json."""
    event_aliases = {
      "acquisition": "job_acquisition",
      "hire": "job_acquisition",
      "hired": "job_acquisition",
      "job_acquisition": "job_acquisition",
      "promotion": "promotion",
      "promoted": "promotion",
      "termination": "termination",
      "terminated": "termination",
      "fired": "termination",
      "laid_off": "termination",
      "transition": "transition",
      "job_transition": "transition",
      "transfer": "transition",
    }
    normalized_type = event_aliases.get(str(event_type).strip().lower(),
                                        str(event_type).strip().lower())

    current_profile = self.get_current_employment_profile()
    status_before = current_profile["employment_status"]
    employer_before = current_profile["employer"]
    job_title_before = current_profile["job_title"]
    workplace_before = current_profile["workplace"]
    timestamp = (self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
                 if self.curr_time else "Unknown time")

    normalized_employment_status = self._normalize_employment_value(
      employment_status)
    normalized_employer = self._normalize_employment_value(employer)
    normalized_job_title = self._normalize_employment_value(job_title)
    normalized_workplace = self._normalize_employment_value(workplace)

    status_after = (normalized_employment_status
                    if normalized_employment_status is not None
                    else current_profile["employment_status"])

    if normalized_type == "job_acquisition":
      status_after = normalized_employment_status or "employed"
    elif normalized_type == "promotion":
      status_after = (normalized_employment_status
                      or current_profile["employment_status"]
                      or "employed")
    elif normalized_type == "termination":
      status_after = normalized_employment_status or "unemployed"
    elif normalized_type == "transition":
      status_after = normalized_employment_status or "employed"

    event_employer = (normalized_employer
                      if normalized_employer is not None
                      else current_profile["employer"])
    event_job_title = (normalized_job_title
                       if normalized_job_title is not None
                       else current_profile["job_title"])
    event_workplace = (normalized_workplace
                       if normalized_workplace is not None
                       else current_profile["workplace"])

    entry = {
      "timestamp": timestamp,
      "event_type": normalized_type,
      "description": description,
      "status_before": status_before,
      "status_after": status_after,
      "employer_before": employer_before,
      "employer": event_employer,
      "job_title_before": job_title_before,
      "job_title": event_job_title,
      "workplace_before": workplace_before,
      "workplace": event_workplace,
      "metadata": metadata or {},
    }

    events = self.get_employment_events()
    events.append(entry)
    if len(events) > 50:
      events = events[-50:]
    self._employment_events_cache = events
    self._write_json_resource(self._get_employment_events_path(), events)

    return entry

  def get_str_daily_plan_req(self): 
    return self.daily_plan_req


  def get_str_curr_date_str(self): 
    return self.curr_time.strftime("%A %B %d")


  def get_curr_event(self):
    if not self.act_address: 
      return (self.name, None, None)
    else: 
      return self.act_event


  def get_curr_event_and_desc(self): 
    if not self.act_address: 
      return (self.name, None, None, None)
    else: 
      return (self.act_event[0], 
              self.act_event[1], 
              self.act_event[2],
              self.act_description)


  def get_curr_obj_event_and_desc(self): 
    if not self.act_address: 
      return ("", None, None, None)
    else: 
      return (self.act_address, 
              self.act_obj_event[1], 
              self.act_obj_event[2],
              self.act_obj_description)


  def add_new_action(self, 
                     action_address, 
                     action_duration,
                     action_description,
                     action_pronunciatio, 
                     action_event,
                     chatting_with, 
                     chat, 
                     chatting_with_buffer,
                     chatting_end_time,
                     act_obj_description, 
                     act_obj_pronunciatio, 
                     act_obj_event, 
                     act_start_time=None): 
    self.act_address = action_address
    self.act_duration = action_duration
    self.act_description = action_description
    self.act_pronunciatio = action_pronunciatio
    self.act_event = action_event

    self.chatting_with = chatting_with
    self.chat = chat 
    if chatting_with_buffer: 
      self.chatting_with_buffer.update(chatting_with_buffer)
    self.chatting_end_time = chatting_end_time

    self.act_obj_description = act_obj_description
    self.act_obj_pronunciatio = act_obj_pronunciatio
    self.act_obj_event = act_obj_event
    
    self.act_start_time = self.curr_time
    
    self.act_path_set = False


  def act_time_str(self): 
    """
    Returns a string output of the current time. 

    INPUT
      None
    OUTPUT 
      A string output of the current time.
    EXAMPLE STR OUTPUT
      "14:05 P.M."
    """
    return self.act_start_time.strftime("%H:%M %p")


  def act_check_finished(self): 
    """
    Checks whether the self.Action instance has finished.  

    INPUT
      curr_datetime: Current time. If current time is later than the action's
                     start time + its duration, then the action has finished. 
    OUTPUT 
      Boolean [True]: Action has finished.
      Boolean [False]: Action has not finished and is still ongoing.
    """
    if not self.act_address: 
      return True
      
    if self.chatting_with: 
      end_time = self.chatting_end_time
    else: 
      x = self.act_start_time
      if x.second != 0: 
        x = x.replace(second=0)
        x = (x + datetime.timedelta(minutes=1))
      end_time = (x + datetime.timedelta(minutes=self.act_duration))

    if end_time.strftime("%H:%M:%S") == self.curr_time.strftime("%H:%M:%S"): 
      return True
    return False


  def act_summarize(self):
    """
    Summarize the current action as a dictionary. 

    INPUT
      None
    OUTPUT 
      ret: A human readable summary of the action.
    """
    exp = dict()
    exp["persona"] = self.name
    exp["address"] = self.act_address
    exp["start_datetime"] = self.act_start_time
    exp["duration"] = self.act_duration
    exp["description"] = self.act_description
    exp["pronunciatio"] = self.act_pronunciatio
    return exp


  def act_summary_str(self):
    """
    Returns a string summary of the current action. Meant to be 
    human-readable.

    INPUT
      None
    OUTPUT 
      ret: A human readable summary of the action.
    """
    start_datetime_str = self.act_start_time.strftime("%A %B %d -- %H:%M %p")
    ret = f"[{start_datetime_str}]\n"
    ret += f"Activity: {self.name} is {self.act_description}\n"
    ret += f"Address: {self.act_address}\n"
    ret += f"Duration in minutes (e.g., x min): {str(self.act_duration)} min\n"
    return ret


  def get_str_daily_schedule_summary(self): 
    ret = ""
    curr_min_sum = 0
    for row in self.f_daily_schedule: 
      curr_min_sum += row[1]
      hour = int(curr_min_sum/60)
      minute = curr_min_sum%60
      ret += f"{hour:02}:{minute:02} || {row[0]}\n"
    return ret


  def get_str_daily_schedule_hourly_org_summary(self): 
    ret = ""
    curr_min_sum = 0
    for row in self.f_daily_schedule_hourly_org: 
      curr_min_sum += row[1]
      hour = int(curr_min_sum/60)
      minute = curr_min_sum%60
      ret += f"{hour:02}:{minute:02} || {row[0]}\n"
    return ret




















