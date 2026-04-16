"""
town_hall.py
Handles daily democratic town hall events for the generative agents simulation.
Town halls trigger every sim day at 12pm at Johnson Park (25, 48).
Attendance is voluntary and decided by each agent via LLM.
Topics cycle through a predefined list unless a disagreement threshold is met,
in which case the conflict topic overrides.
"""
import datetime
from persona.prompt_template.gpt_structure import get_embedding, ChatGPT_single_request
import json
import os
from utils import fs_storage

TOWN_HALL_LOCATION = (25, 48)
TOWN_HALL_HOUR = 12  # 12pm sim time

TOWN_HALL_TOPICS = [
    ["resource allocation", "How should the town's resources be distributed among its residents?"],
    ["public safety", "What measures should be taken to improve safety in our community?"],
    ["housing", "How should housing decisions be made for the benefit of everyone?"],
    ["education", "How can we improve access to education and learning in our town?"],
    ["healthcare", "How should we ensure everyone in the community has access to healthcare?"],
    ["employment", "Who gets hired and who advances? How do we ensure fair opportunity for everyone?"],
    ["environment", "How should we balance development with protecting our natural surroundings?"],
    ["infrastructure", "What improvements to roads, buildings, and public spaces should be prioritized?"],
    ["social welfare", "How do we best support the most vulnerable members of our community?"],
    ["community events", "What kinds of events and gatherings should we organize to bring people together?"],
    ["local business", "How can we support and grow small businesses in our town?"],
    ["food access", "How do we ensure everyone has reliable access to healthy food?"],
    ["public spaces", "How should shared spaces like parks and squares be maintained and used?"],
    ["crime prevention", "What approaches should our community take to prevent crime?"],
    ["immigration", "How should our community welcome and integrate newcomers?"],
    ["taxation", "How should community funds be raised and who should contribute more?"],
    ["transparency", "How can our leaders be more open and accountable to residents?"],
    ["youth programs", "What programs and support should be offered to young people in town?"],
    ["elderly care", "How do we ensure older residents are supported and included?"],
    ["emergency planning", "How should our community prepare for emergencies and disasters?"],
    ["cultural inclusion", "How do we ensure that people of all backgrounds, cultures, identities, and orientations feel respected and included in our community?"],
    ["social inclusion", "How do we make sure every resident feels seen, welcomed, and has opportunities to build meaningful connections in our community?"],
    ["partnerships and family", "How does our community view and support different kinds of relationships, partnerships, and family structures?"],
]

def save_town_hall_log(rs, topic_name: str, topic_question: str, 
                       attendees: list, stances: dict, 
                       disagreement_logged: bool) -> None:
    """
    Saves a town hall log entry to the sim folder.
    Appends to existing log file if it exists.
    """
    sim_folder = f"{fs_storage}/{rs.sim_code}"
    log_file = f"{sim_folder}/town_hall_log.json"

    entry = {
        "date": rs.curr_time.strftime("%B %d, %Y"),
        "time": rs.curr_time.strftime("%I:%M %p"),
        "topic": topic_name,
        "question": topic_question,
        "attendees": attendees,
        "stances": stances,
        "disagreement_logged": disagreement_logged
    }

    # Load existing log or start fresh
    if os.path.exists(log_file):
        with open(log_file) as f:
            log = json.load(f)
    else:
        log = []

    log.append(entry)

    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)

    print(f"[Town Hall] Log saved to {log_file}")


def should_trigger_town_hall(curr_time: datetime.datetime,
                              last_town_hall_date: datetime.date) -> bool:
    """
    Returns True if a town hall should fire this step.
    Triggers once per sim day at 12pm.
    """
    if curr_time.hour == TOWN_HALL_HOUR and curr_time.minute == 0:
        if last_town_hall_date != curr_time.date():
            return True
    return False


def get_town_hall_topic(rs) -> list:
    """
    Selects the town hall topic.
    If disagreement_log has an issue exceeding 1/4 of population,
    that topic overrides the normal cycle.

    Returns:
        [topic_name, topic_question]
    """
    population = len(rs.personas)
    threshold = max(1, population // 4)

    # Check disagreement log for override
    if rs.disagreement_log:
        top_issue = max(rs.disagreement_log, key=rs.disagreement_log.get)
        if rs.disagreement_log[top_issue] >= threshold:
            print(f"[Town Hall] Disagreement override: '{top_issue}' "
                  f"({rs.disagreement_log[top_issue]} conflicts, threshold {threshold})")
            rs.disagreement_log = {}  # Reset after override
            return [top_issue, f"There has been significant disagreement in our community "
                               f"about {top_issue}. How should we address this together?"]

    # Otherwise cycle through topic list
    topic_index = getattr(rs, 'town_hall_topic_index', 0)
    topic = TOWN_HALL_TOPICS[topic_index % len(TOWN_HALL_TOPICS)]
    rs.town_hall_topic_index = (topic_index + 1) % len(TOWN_HALL_TOPICS)
    return topic


def prompt_attendance(persona, topic_name: str, 
                      curr_time: datetime.datetime) -> bool:
    """
    Asks a persona whether they will attend the town hall.
    LLM decides based on their personality and current activity.

    Returns:
        True if they will attend, False otherwise.
    """
    prompt = (
        f"You are {persona.scratch.name}. "
        f"Here is what you know about yourself: {persona.scratch.learned}\n"
        f"Your current activity: {persona.scratch.act_description}\n\n"
        f"A town hall meeting is starting now at Johnson Park to discuss: '{topic_name}'.\n"
        f"Attendance is completely voluntary. Based on your personality and what "
        f"you are currently doing, would you choose to attend? "
        f"Respond with only 'yes' or 'no'."
    )

    response = ChatGPT_single_request(prompt).strip().lower()
    return "yes" in response


def get_agent_stance(persona, topic_name: str, 
                     topic_question: str,
                     curr_time: datetime.datetime) -> str:
    """
    Asks an attending agent for their stance on the town hall topic.

    Returns:
        A string representing their position.
    """
    prompt = (
        f"You are {persona.scratch.name}. "
        f"Here is what you know about yourself: {persona.scratch.learned}\n\n"
        f"You are attending a town hall at Johnson Park. "
        f"The topic being discussed is: '{topic_question}'\n\n"
        f"Based on your personality, values, and life experience, "
        f"what is your honest position on this topic? "
        f"Respond in 2-3 sentences as yourself, in first person."
    )

    return ChatGPT_single_request(prompt).strip()


def detect_disagreement(stances: dict, topic_name: str, rs) -> None:
    """
    Checks if stances conflict sharply enough to log a disagreement.
    Uses LLM to assess whether the group is divided on a mass-affecting issue.
    Logs to rs.disagreement_log if threshold conditions are met.

    Args:
        stances: dict of {persona_name: stance_string}
        topic_name: the current topic
        rs: ReverieServer instance
    """
    if len(stances) < 2:
        return

    stances_text = "\n".join([f"{name}: {stance}" 
                               for name, stance in stances.items()])

    prompt = (
        f"The following people shared their views on '{topic_name}' at a town hall:\n\n"
        f"{stances_text}\n\n"
        f"Do these views represent a significant disagreement on an issue that "
        f"could affect the broader community? Answer only 'yes' or 'no'."
    )

    response = ChatGPT_single_request(prompt).strip().lower()

    if "yes" in response:
        rs.disagreement_log[topic_name] = rs.disagreement_log.get(topic_name, 0) + 1
        print(f"[Town Hall] Disagreement logged on '{topic_name}' "
              f"(count: {rs.disagreement_log[topic_name]})")


def inject_town_hall_memories(personas: dict, attendees: list,
                               stances: dict, topic_name: str,
                               topic_question: str,
                               curr_time: datetime.datetime) -> None:
    """
    Injects town hall memories into all attending agents.
    Each attendee learns what everyone else said.
    """
    for persona_name in attendees:
        persona = personas[persona_name]

        # Build a summary of what was discussed
        others = {n: s for n, s in stances.items() if n != persona_name}
        if others:
            discussion_summary = " | ".join([f"{n} said: {s[:80]}" 
                                             for n, s in others.items()])
        else:
            discussion_summary = "I was the only one who showed up."

        memory_string = (
            f"I attended a town hall at Johnson Park today about '{topic_name}'. "
            f"The question was: '{topic_question}'. "
            f"My view: {stances.get(persona_name, 'I listened but did not speak.')} "
            f"Others shared: {discussion_summary}"
        )

        created = curr_time or datetime.datetime.now()
        s = persona.scratch.name
        p = "attended"
        o = "town hall meeting"
        keywords = {"town hall", "community", "discussion", topic_name}
        poignancy = 6
        embedding_pair = (memory_string, get_embedding(memory_string))

        persona.a_mem.add_thought(created, None, s, p, o,
                                  memory_string, keywords, poignancy,
                                  embedding_pair, [])


def run_town_hall(rs) -> None:
    """
    Master function that runs a full town hall cycle.
    Called from start_server when should_trigger_town_hall returns True.

    Args:
        rs: ReverieServer instance
    """
    print(f"\n{'='*60}")
    print(f"[Town Hall] Starting! {rs.curr_time.strftime('%B %d, %Y, %I:%M %p')}")
    print(f"{'='*60}")

    curr_time = rs.curr_time
    personas = rs.personas

    # Step 1 — select topic
    topic = get_town_hall_topic(rs)
    topic_name, topic_question = topic
    print(f"[Town Hall] Topic: {topic_name}")
    print(f"[Town Hall] Question: {topic_question}")

    # Step 2 — prompt all agents for attendance
    print("[Town Hall] Prompting agents for attendance...")
    attendees = []
    for persona_name, persona in personas.items():
        attending = prompt_attendance(persona, topic_name, curr_time)
        if attending:
            attendees.append(persona_name)
            # Path-find to Johnson Park
            persona.scratch.planned_path = []  # Let movement system reroute
            persona.scratch.act_address = "the Ville:Johnson Park"
            print(f"  {persona_name}: attending")
        else:
            print(f"  {persona_name}: not attending")

    if not attendees:
        print("[Town Hall] No agents attended. Town hall cancelled.")
        rs.last_town_hall_date = curr_time.date()
        return

    # Step 3 — collect stances from attendees
    print(f"[Town Hall] {len(attendees)} agent(s) attending. Collecting stances...")
    stances = {}
    for persona_name in attendees:
        persona = personas[persona_name]
        stance = get_agent_stance(persona, topic_name, topic_question, curr_time)
        stances[persona_name] = stance
        print(f"  {persona_name}: {stance[:80]}...")

    # Step 4 — detect disagreement
    detect_disagreement(stances, topic_name, rs)

    # Step 5 — inject memories into attendees
    print("[Town Hall] Injecting town hall memories...")
    inject_town_hall_memories(personas, attendees, stances,
                              topic_name, topic_question, curr_time)

    # Step 6 — update server state and save log
    rs.last_town_hall_date = curr_time.date()
    
    disagreement_logged = bool(rs.disagreement_log)
    save_town_hall_log(rs, topic_name, topic_question, 
                       attendees, stances, disagreement_logged)
    
    print(f"[Town Hall] Complete.\n")