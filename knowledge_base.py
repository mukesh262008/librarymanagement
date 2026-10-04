"""Library policy facts and rule definitions used by the decision service."""

POLICY_VALUES = {
    "max_active_loans": 5,
    "loan_period_days": 21,
    "overdue_restriction": True,
    "daily_fine": 0.30,
    "renewal_limit": 1,
    "fine_restriction": 10.00,
}


def load_policy_values(db) -> dict:
    """Read the active, structured policy values used by circulation checks."""
    rows = db.execute(
        "SELECT policy_key, value FROM policies WHERE active = 1"
    ).fetchall()
    stored = {row["policy_key"]: row["value"] for row in rows}
    def as_bool(value):
        normalized = value.lower()
        if normalized not in {"true", "false"}:
            raise ValueError("Boolean policy values must be true or false.")
        return normalized == "true"

    converters = {
        "max_active_loans": int,
        "loan_period_days": int,
        "overdue_restriction": as_bool,
        "daily_fine": float,
        "renewal_limit": int,
        "fine_restriction": float,
    }
    missing = set(converters) - stored.keys()
    if missing:
        raise RuntimeError(f"Required active library policy is missing: {', '.join(sorted(missing))}.")
    try:
        values = {key: converters[key](stored[key]) for key in converters}
    except (TypeError, ValueError) as exc:
        raise RuntimeError("A stored library policy value is invalid.") from exc
    if (
        values["max_active_loans"] < 1
        or values["loan_period_days"] < 1
        or values["daily_fine"] < 0
        or values["renewal_limit"] < 0
        or values["fine_restriction"] < 0
    ):
        raise RuntimeError("A stored library policy value is outside its valid range.")
    return values


ISSUE_RULES = (
    (("member_active",), "member_eligible"),
    (("member_has_overdue",), "borrowing_restricted"),
    (("member_fines_at_limit",), "borrowing_restricted"),
    (("member_at_loan_limit",), "borrowing_restricted"),
    (("book_available",), "book_can_be_issued"),
    (("member_eligible", "book_can_be_issued", "not_borrowing_restricted"), "issue_approved"),
)

RENEWAL_RULES = (
    (("loan_active",), "loan_can_be_renewed"),
    (("member_has_overdue",), "renewal_restricted"),
    (("renewal_limit_reached",), "renewal_restricted"),
    (("member_active", "loan_can_be_renewed", "not_renewal_restricted"), "renewal_approved"),
)


def forward_chain(facts: set[str], rules: tuple) -> set[str]:
    """Derive all reachable propositions from the grounded policy rules."""
    derived = set(facts)
    changed = True
    while changed:
        changed = False
        for premises, conclusion in rules:
            if all(premise in derived for premise in premises) and conclusion not in derived:
                derived.add(conclusion)
                changed = True
    return derived


def backward_chain(goal: str, facts: set[str], rules: tuple, seen: set[str] | None = None) -> bool:
    """Check a requested conclusion by proving its premises recursively."""
    if goal.startswith("not_"):
        return goal[4:] not in facts
    if goal in facts:
        return True
    seen = set() if seen is None else seen
    if goal in seen:
        return False
    seen.add(goal)
    return any(
        all(backward_chain(premise, facts, rules, seen.copy()) for premise in premises)
        for premises, conclusion in rules if conclusion == goal
    )


def resolution_refutes(clauses: list[frozenset[str]], query: str) -> bool:
    """Use propositional resolution to test whether the clauses entail a query."""
    working = set(clauses)
    working.add(frozenset({f"not_{query}"}))
    while True:
        additions: set[frozenset[str]] = set()
        ordered = list(working)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                for literal in left:
                    complement = literal[4:] if literal.startswith("not_") else f"not_{literal}"
                    if complement in right:
                        resolvent = frozenset((left | right) - {literal, complement})
                        if not resolvent:
                            return True
                        additions.add(resolvent)
        if additions.issubset(working):
            return False
        working.update(additions)


def clauses_for_facts_and_rules(facts: set[str], rules: tuple) -> list[frozenset[str]]:
    """Ground the current facts and implication rules as propositional clauses."""
    clauses = [frozenset({fact}) for fact in facts]
    clauses.extend(
        frozenset({*(f"not_{premise}" for premise in premises), conclusion})
        for premises, conclusion in rules
    )
    return clauses
