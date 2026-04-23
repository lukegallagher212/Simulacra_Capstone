"""
leader.py
Handles leader duty injection for both democratic and authoritarian societies.
Leaders have their daily routine replaced with leadership responsibilities.
Their personality traits shape how they carry out these duties.
"""
import datetime
from persona.prompt_template.gpt_structure import get_embedding, ChatGPT_single_request


# ============================================================================
# LEADER DUTY DEFINITIONS
# ============================================================================

DEMOCRATIC_LEADER_DUTIES = """I have been elected as the leader of this community. \
My responsibilities today are to review the outcomes of recent town hall discussions, \
make policy decisions on behalf of my community, and hold open office hours where \
any resident can come speak with me. I document my reasoning transparently so that \
the community understands how decisions are made. How I carry out these duties \
reflects who I am as a person."""

AUTHORITARIAN_LEADER_DUTIES = """I am the appointed leader of this community. \
My responsibilities today are to issue directives, review internal reports on the \
state of the community, make decisions that maintain order and stability, and ensure \
that my policies are being followed. My decisions are final and immediate. How I \
carry out these duties reflects who I am as a person."""


# ============================================================================
# SPAWN AND WORK LOCATION (stub — fill in once map is ready)
# ============================================================================

# def get_leader_spawn_location(society_type: str) -> tuple:
#     """
#     Returns the (x, y) tile coordinate where the leader spawns each day.
#     Democratic: town hall / community center
#     Authoritarian: seat of power / government building
#     """
#     if society_type == "democratic":
#         return (25, 48)  # Johnson Park placeholder — replace with actual office tile
#     elif society_type == "authoritarian":
#         return (25, 48)  # Replace with authoritarian seat of power tile
#     return (25, 48)


# def get_leader_work_location(society_type: str) -> str:
#     """
#     Returns the act_address string for the leader's work location.
#     Democratic: public-facing location
#     Authoritarian: secure/private government location
#     """
#     if society_type == "democratic":
#         return "the Ville:Johnson Park"  # Replace with actual office address
#     elif society_type == "authoritarian":
#         return "the Ville:Johnson Park"  # Replace with authoritarian HQ address
#     return "the Ville:Johnson Park"


# ============================================================================
# DUTY INJECTION
# ============================================================================

def inject_leader_duties(persona, society_type: str, 
                         curr_time: datetime.datetime) -> None:
    """
    Injects leadership duties into the leader persona's memory stream.
    Replaces their normal daily routine priorities with leadership responsibilities.
    Their existing personality traits shape how they carry out these duties.

    Args:
        persona: the leader persona object
        society_type: 'democratic' or 'authoritarian'
        curr_time: current simulation time
    """
    if society_type == "democratic":
        duty_string = DEMOCRATIC_LEADER_DUTIES
    else:
        duty_string = AUTHORITARIAN_LEADER_DUTIES

    created = curr_time or datetime.datetime.now()
    s = persona.scratch.name
    p = "has responsibilities as"
    o = "community leader"
    keywords = {"leader", "duties", "policy", "community", society_type}
    poignancy = 9  # High — this shapes their entire day
    embedding_pair = (duty_string, get_embedding(duty_string))

    persona.a_mem.add_thought(created, None, s, p, o,
                              duty_string, keywords, poignancy,
                              embedding_pair, [])

    # Stamp on scratch for fast backend access
    persona.scratch.leader_duties = duty_string
    persona.scratch.is_leader = True

    print(f"[Leader] Duties injected for {persona.scratch.name} "
          f"({society_type} leader)")


def update_leader_daily_plan(persona, society_type: str,
                              curr_time: datetime.datetime) -> None:
    """
    Overrides the leader's daily plan requirement with leadership duties.
    This replaces their normal daily_plan_req so the schedule generator
    produces a leadership-focused day instead of their usual routine.

    Args:
        persona: the leader persona object
        society_type: 'democratic' or 'authoritarian'
        curr_time: current simulation time
    """
    if society_type == "democratic":
        new_plan = (
            f"{persona.scratch.name} is the elected leader of the community. "
            f"Today they will review recent town hall outcomes, make policy "
            f"decisions on behalf of residents, and hold open office hours "
            f"for any community member who wishes to speak with them."
        )
    else:
        new_plan = (
            f"{persona.scratch.name} is the appointed leader of the community. "
            f"Today they will issue directives, review reports on community "
            f"activity, make decisions to maintain order and stability, and "
            f"ensure their policies are being followed."
        )

    # Override their daily plan requirement
    persona.scratch.daily_plan_req = new_plan

    print(f"[Leader] Daily plan overridden for {persona.scratch.name}")


def setup_leader(persona, society_type: str,
                 curr_time: datetime.datetime) -> None:
    """
    Master function that sets up a persona as the active leader.
    Injects duties into memory and overrides their daily plan.
    Call this once when a leader is assigned or elected.

    Args:
        persona: the leader persona object
        society_type: 'democratic' or 'authoritarian'
        curr_time: current simulation time
    """
    print(f"\n[Leader] Setting up {persona.scratch.name} "
          f"as {society_type} leader...")

    # Step 1 — inject duty memory
    inject_leader_duties(persona, society_type, curr_time)

    # Step 2 — override daily plan
    update_leader_daily_plan(persona, society_type, curr_time)

    # Step 3 — spawn/work location (commented out until map is ready)
    # spawn = get_leader_spawn_location(society_type)
    # work = get_leader_work_location(society_type)
    # persona.scratch.act_address = work
    # persona.scratch.planned_path = []

    print(f"[Leader] {persona.scratch.name} is ready.\n")