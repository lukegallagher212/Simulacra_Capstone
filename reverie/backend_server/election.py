"""
election.py
Handles democratic elections for the generative agents simulation.
Elections trigger on Day 1 and every 7 sim days after.
"""
import random
import datetime
from persona.prompt_template.gpt_structure import get_embedding, ChatGPT_single_request


ELECTION_INTERVAL_DAYS = 7


def should_trigger_election(curr_time: datetime.datetime, 
                             last_election_day: int, 
                             sim_start_time: datetime.datetime) -> bool:
    """
    Returns True if an election should fire this step.
    Triggers on Day 1 and every 7 sim days after.
    """
    curr_day = (curr_time - sim_start_time).days + 1

    # Day 1 trigger
    if curr_day == 1 and last_election_day == 0:
        return True

    # Every 7 days after
    if curr_day - last_election_day >= ELECTION_INTERVAL_DAYS:
        return True

    return False


def inject_election_memory(persona, curr_time: datetime.datetime):
    """
    Injects a suggestive election awareness memory into a persona.
    Political affinity agents get a more personal, reflective version.
    Non-affinity agents get a neutral awareness memory.
    """
    has_affinity = getattr(persona, 'political_affinity', False)

    if has_affinity:
        memory_string = (
            "There is an election coming up in the community. As someone who "
            "cares about politics, I find myself thinking about whether I should "
            "speak up, share my views, or even put myself forward as a candidate."
        )
    else:
        memory_string = (
            "I heard there is an election coming up in the community soon."
        )

    created = curr_time or datetime.datetime.now()
    expiration = None
    s = persona.scratch.name
    p = "is aware of"
    o = "upcoming election"
    keywords = {"election", "community", "vote", "candidate"}
    poignancy = 7 if has_affinity else 4
    embedding_pair = (memory_string, get_embedding(memory_string))
    filling = []

    persona.a_mem.add_thought(created, expiration, s, p, o,
                              memory_string, keywords, poignancy,
                              embedding_pair, filling)


def run_vote(persona, all_persona_names: list, curr_time: datetime.datetime) -> str:
    """
    Asks a persona who they would vote for given what they know about everyone.
    Returns the name of their chosen candidate.
    """
    candidates = [n for n in all_persona_names if n != persona.scratch.name]
    candidates_str = ", ".join(candidates + [persona.scratch.name])

    prompt = (
        f"You are {persona.scratch.name}. "
        f"Here is what you know about yourself: {persona.scratch.learned}\n\n"
        f"An election is being held in your community. "
        f"The candidates are: {candidates_str}.\n\n"
        f"Based on your personality, values, and what you know about these people, "
        f"who would you vote for? Respond with only the full name of your chosen candidate, "
        f"nothing else."
    )

    response = ChatGPT_single_request(prompt).strip()

    # Validate response is an actual candidate name
    for name in all_persona_names:
        if name.lower() in response.lower():
            return name

    # Fallback if LLM response is unrecognizable
    return random.choice(all_persona_names)


def tally_votes(votes: dict) -> str:
    """
    Tallies votes and returns the winner.
    In the event of a tie, winner is chosen randomly (agents never know).

    Args:
        votes: dict of {voter_name: voted_for_name}

    Returns:
        Name of the winning candidate.
    """
    tally = {}
    for voted_for in votes.values():
        tally[voted_for] = tally.get(voted_for, 0) + 1

    max_votes = max(tally.values())
    winners = [name for name, count in tally.items() if count == max_votes]

    if len(winners) > 1:
        print(f"[Election] Tie between: {winners}. Resolving randomly.")

    return random.choice(winners)


def inject_result_memories(personas: dict, winner_name: str, 
                           curr_time: datetime.datetime):
    """
    Injects election result memories into all personas.
    Winner gets a personal victory memory.
    Everyone else learns who won.
    """
    for persona_name, persona in personas.items():
        if persona_name == winner_name:
            memory_string = (
                f"I was elected as the leader of our community by my peers. "
                f"I feel a sense of responsibility to serve them well."
            )
            poignancy = 9
        else:
            memory_string = (
                f"{winner_name} was elected as the leader of our community. "
                f"I will respect the outcome of the election."
            )
            poignancy = 6

        created = curr_time or datetime.datetime.now()
        s = persona.scratch.name
        p = "learned about"
        o = "election result"
        keywords = {"election", "leader", "result", winner_name}
        embedding_pair = (memory_string, get_embedding(memory_string))

        persona.a_mem.add_thought(created, None, s, p, o,
                                  memory_string, keywords, poignancy,
                                  embedding_pair, [])

        # Update scratch so backend always knows current leader
        persona.scratch.leader = winner_name


def run_election(rs) -> str:
    """
    Master function that runs a full election cycle.
    Called from start_server when should_trigger_election returns True.

    Args:
        rs: ReverieServer instance

    Returns:
        Name of the elected leader.
    """
    print(f"\n{'='*60}")
    print(f"[Election] Election triggered! {rs.curr_time.strftime('%B %d, %Y')}")
    print(f"{'='*60}")

    personas = rs.personas
    all_names = list(personas.keys())
    curr_time = rs.curr_time

    # Step 1 — inject campaign awareness memories
    print("[Election] Injecting campaign awareness memories...")
    for persona in personas.values():
        inject_election_memory(persona, curr_time)

    # Step 2 — each persona votes
    print("[Election] Collecting votes...")
    votes = {}
    for persona_name, persona in personas.items():
        vote = run_vote(persona, all_names, curr_time)
        votes[persona_name] = vote
        print(f"  {persona_name:20s} voted for: {vote}")

    # Step 3 — tally and determine winner
    winner = tally_votes(votes)
    print(f"\n[Election] Winner: {winner}")

    # Step 4 — inject result memories into all agents
    print("[Election] Injecting result memories...")
    inject_result_memories(personas, winner, curr_time)

    # Step 5 — update server state
    rs.leader = winner
    rs.last_election_day = (curr_time - rs.start_time).days + 1
    print(f"[Election] Complete. {winner} is the new leader.\n")

    return winner