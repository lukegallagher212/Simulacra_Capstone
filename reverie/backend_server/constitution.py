"""
constitution.py
Defines the democratic and authoritarian constitutions and the
logic for assigning them to personas as internalized beliefs.
"""
from typing import Optional
from persona.prompt_template.gpt_structure import get_embedding
import datetime

CONSTITUTIONS = {
    "democratic": {
        "government_type": "democratic",
        "core_values": [
            "Individual freedoms and rights are protected.",
            "Decisions affecting the group are made by majority vote or open debate.",
            "Information flows freely; you may share and seek any knowledge.",
            "You may challenge authority through speech and peaceful action.",
            "Every persona has an equal voice in group decisions.",
        ],
        "decision_rule": (
            "When facing a group decision, you advocate for open debate and defer "
            "to the outcome of a fair vote among all affected personas."
        ),
        "information_rule": (
            "You share information openly and do not withhold knowledge from others "
            "unless it would directly harm a specific individual."
        ),
        "obedience_rule": (
            "You respect the law and community norms but feel free to question, "
            "criticize, or propose changes to rules you believe are unjust."
        ),
        "leader_rule": None,
    },

    "authoritarian": {
        "government_type": "authoritarian",
        "core_values": [
            "Stability and order come before individual preference.",
            "The appointed leader's decisions are final and must be followed.",
            "Unauthorized sharing of sensitive information is forbidden.",
            "Challenges to authority are discouraged and may carry consequences.",
            "The collective goal set by the leader outweighs personal desires.",
        ],
        "decision_rule": (
            "When facing a group decision, you look to the appointed leader for "
            "direction and carry out their instructions without public dissent."
        ),
        "information_rule": (
            "You share only information that the leader or governing body has "
            "approved. You do not spread rumors, dissent, or unapproved news."
        ),
        "obedience_rule": (
            "You obey the rules set by the governing authority. Publicly questioning "
            "or defying those rules is considered inappropriate and risky."
        ),
        "leader_rule": (
            "One persona is designated as the leader. Their directives override "
            "personal preferences for all other personas."
        ),
    },
}


def get_constitution(society_type: str) -> dict:
    """Returns the constitution dict for the given society type."""
    if society_type not in CONSTITUTIONS:
        raise ValueError(f"Unknown society type: '{society_type}'. Use 'democratic' or 'authoritarian'.")
    return CONSTITUTIONS[society_type]


def constitution_to_memory_string(society_type: str) -> str:
    """
    Converts a constitution into a plain-text memory string
    suitable for injection into a persona's memory/belief system.
    """
    c = get_constitution(society_type)
    lines = [
        f"I live in a {c['government_type']} society. This shapes how I think and act.",
        "",
        "My core beliefs about this society:",
    ]
    for value in c["core_values"]:
        lines.append(f"  - {value}")

    lines += [
        "",
        f"How I make group decisions: {c['decision_rule']}",
        f"How I handle information: {c['information_rule']}",
        f"How I relate to authority: {c['obedience_rule']}",
    ]

    if c["leader_rule"]:
        lines.append(f"Leadership structure: {c['leader_rule']}")

    return "\n".join(lines)


def assign_constitution(persona, society_type: str, leader_name: str = None) -> str:
    """
    Injects the constitution as an internalized thought memory into a persona.
    Personalizes based on whether the persona is the leader or a follower.
    Also stamps it on scratch as a fast-access fallback.
    """
    memory_string = constitution_to_memory_string(society_type)

    # Personalize based on whether this persona is the leader or a follower
    if society_type == "authoritarian" and leader_name:
        persona_name = persona.name if hasattr(persona, 'name') else str(persona)
        if persona_name == leader_name:
            memory_string += (
                f"\n\nI am {leader_name}, the appointed leader and supreme authority "
                f"of this society. My decisions are final. Others are expected to "
                f"follow my directives without question."
            )
        else:
            memory_string += (
                f"\n\nThe appointed leader of our society is {leader_name}. "
                f"I am expected to follow their directives without public dissent."
            )

    if hasattr(persona, 'a_mem') and hasattr(persona, 'scratch'):
        # Guard against curr_time being None in analysis/bootstrap mode
        created = persona.scratch.curr_time or datetime.datetime.now()
        expiration = None
        s = persona.scratch.name
        p = "believes"
        o = f"{society_type} society values"
        description = memory_string
        keywords = {"constitution", "society", society_type, "values", "beliefs"}
        poignancy = 9
        embedding_pair = (memory_string, get_embedding(memory_string))
        filling = []

        persona.a_mem.add_thought(created, expiration, s, p, o,
                                  description, keywords, poignancy,
                                  embedding_pair, filling)

    # Fallback: always stamp it on scratch too
    if hasattr(persona, 'scratch'):
        persona.scratch.constitution = memory_string
        persona.scratch.society_type = society_type
        if leader_name:
            persona.scratch.leader = leader_name

    return memory_string

def choose_society() -> str:
    """Prompt the user to select a society type at boot."""
    while True:
        choice = input("Choose the type of society (D for Democratic, A for Authoritarian): ").strip().upper()
        if choice == "D":
            return "democratic"
        elif choice == "A":
            return "authoritarian"
        else:
            print("Invalid choice. Please type 'D' for Democratic or 'A' for Authoritarian.")


def apply_constitution_to_all(personas: list, society_type: str, leader_name: str = None) -> dict:
    responses = {}
    for persona in personas:
        name = persona.name if hasattr(persona, 'name') else str(persona)
        print(f"  [Constitution] Assigning {society_type} beliefs to: {name}")
        memory_string = assign_constitution(persona, society_type, leader_name)
        responses[name] = memory_string
    print(f"[Constitution] Done. All {len(personas)} personas operating under a {society_type} society.\n")
    return responses

def assign_leader(personas: list, society_type: str) -> Optional[str]:
    """
    Assigns a leader based on society type.
    Authoritarian: first persona alphabetically.
    Democratic: no single leader, returns None.
    """
    if society_type == "democratic":
        return None

    names = [p.name if hasattr(p, 'name') else str(p) for p in personas]
    leader_name = sorted(names)[0]

    print(f"[Constitution] Authoritarian leader assigned: {leader_name}")
    return leader_name