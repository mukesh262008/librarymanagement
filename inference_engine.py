from __future__ import annotations

from database import get_db
from knowledge_base import (
    ISSUE_RULES,
    RENEWAL_RULES,
    backward_chain,
    clauses_for_facts_and_rules,
    forward_chain,
    load_policy_values,
    resolution_refutes,
)


def _number(value) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("An identifier must be a number.") from exc
    if result < 1:
        raise ValueError("An identifier must be positive.")
    return result


def _member_state(member_id: int):
    db = get_db()
    member = db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if member is None:
        return None
    active_loans = db.execute(
        "SELECT COUNT(*) AS count FROM loans WHERE member_id = ? AND status = 'active'",
        (member_id,),
    ).fetchone()["count"]
    overdue = db.execute(
        "SELECT COUNT(*) AS count FROM loans WHERE member_id = ? AND status = 'active' AND due_on < date('now')",
        (member_id,),
    ).fetchone()["count"]
    fine_total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM fines WHERE member_id = ? AND paid_on IS NULL",
        (member_id,),
    ).fetchone()["total"]
    return member, active_loans, overdue, float(fine_total)


def _policy_result(approved: bool, reason: str | None, policy: str, condition: str, result: str) -> dict:
    return {
        "approved": approved,
        "reason": reason,
        "details": {
            "decision": "Approved" if approved else "Not approved",
            "policy": policy,
            "condition": condition,
            "result": result,
        },
    }


def evaluate_request(action: str, member_id, book_id=None, loan_id=None) -> dict:
    action = str(action or "").lower()
    if action not in {"issue", "renew"}:
        raise ValueError("Unsupported circulation action.")
    policies = load_policy_values(get_db())
    if action == "renew":
        if loan_id is None:
            raise ValueError("A loan is required.")
        loan_id = _number(loan_id)
        loan = get_db().execute(
            "SELECT l.*, b.title, m.name AS member_name FROM loans l "
            "JOIN books b ON b.id = l.book_id JOIN members m ON m.id = l.member_id WHERE l.id = ?",
            (loan_id,),
        ).fetchone()
        if loan is None:
            return {"error": "Loan not found."}
        member_id = loan["member_id"]
        state = _member_state(member_id)
        member, _active_count, overdue_count, fine_total = state
        facts = {"member_active"} if member["status"] == "active" else set()
        if overdue_count and policies["overdue_restriction"]:
            facts.add("member_has_overdue")
        if loan["status"] == "active":
            facts.add("loan_active")
        if loan["renewals"] >= policies["renewal_limit"]:
            facts.add("renewal_limit_reached")
        if "member_has_overdue" in facts or "renewal_limit_reached" in facts:
            facts.add("renewal_restricted")
        else:
            facts.add("not_renewal_restricted")
        derived = forward_chain(facts, RENEWAL_RULES)
        approved = backward_chain("renewal_approved", facts, RENEWAL_RULES)
        clauses = clauses_for_facts_and_rules(facts, RENEWAL_RULES)
        reason = None
        if "member_active" not in facts:
            reason = "Member account is not active."
        elif "loan_active" not in facts:
            reason = "This loan is no longer active."
        elif overdue_count and policies["overdue_restriction"]:
            reason = "Member has an overdue item."
        elif loan["renewals"] >= policies["renewal_limit"]:
            reason = "This loan has reached its renewal limit."
        return _policy_result(
            approved and "renewal_approved" in derived and resolution_refutes(clauses, "renewal_approved"),
            reason,
            f"Eligible loans may be renewed {policies['renewal_limit']} time(s). Overdue items restrict renewals.",
            f"{overdue_count} overdue item{'s' if overdue_count != 1 else ''}; {loan['renewals']} renewal(s) used.",
            f"The due date can be extended by {policies['loan_period_days']} days." if approved else "This loan cannot be renewed.",
        )

    if member_id is None or book_id is None:
        raise ValueError("A member and book are required.")
    member_id, book_id = _number(member_id), _number(book_id)
    db = get_db()
    state = _member_state(member_id)
    book = db.execute(
        "SELECT b.*, b.total_copies - (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.status = 'active') AS available_copies "
        "FROM books b WHERE b.id = ?", (book_id,),
    ).fetchone()
    if state is None:
        return {"error": "Member not found."}
    if book is None:
        return {"error": "Book not found."}
    member, active_count, overdue_count, fine_total = state
    facts = {"member_active"} if member["status"] == "active" else set()
    if overdue_count and policies["overdue_restriction"]:
        facts.add("member_has_overdue")
    if fine_total >= policies["fine_restriction"]:
        facts.add("member_fines_at_limit")
    if active_count >= policies["max_active_loans"]:
        facts.add("member_at_loan_limit")
    if book["available_copies"] > 0:
        facts.add("book_available")
    restriction_facts = {"member_has_overdue", "member_fines_at_limit", "member_at_loan_limit"}
    if facts & restriction_facts:
        facts.add("borrowing_restricted")
    else:
        facts.add("not_borrowing_restricted")
    derived = forward_chain(facts, ISSUE_RULES)
    approved = backward_chain("issue_approved", facts, ISSUE_RULES)
    clauses = clauses_for_facts_and_rules(facts, ISSUE_RULES)
    reason = None
    if member["status"] != "active":
        reason = "Member account is not active."
    elif overdue_count and policies["overdue_restriction"]:
        reason = "Member has an overdue item."
    elif fine_total >= policies["fine_restriction"]:
        reason = "Outstanding fines meet the borrowing threshold."
    elif active_count >= policies["max_active_loans"]:
        reason = "Member has reached the borrowing limit."
    elif book["available_copies"] < 1:
        reason = "No copies of this title are currently available."
    if reason == "Member account is not active.":
        policy = "Borrowing is available to active members only."
    elif reason == "Member has an overdue item.":
        policy = "Overdue items restrict new borrowing until the account is clear."
    elif reason == "Outstanding fines meet the borrowing threshold.":
        policy = f"Outstanding balances of ${policies['fine_restriction']:.2f} or more restrict new borrowing."
    elif reason == "Member has reached the borrowing limit.":
        policy = f"Members may hold up to {policies['max_active_loans']} active loans."
    elif reason == "No copies of this title are currently available.":
        policy = "Only currently available copies can be issued."
    else:
        policy = f"Active members may borrow up to {policies['max_active_loans']} available items within their account limits."
    return _policy_result(
        approved and "issue_approved" in derived and resolution_refutes(clauses, "issue_approved"),
        reason,
        policy,
        f"{overdue_count} overdue item{'s' if overdue_count != 1 else ''}; ${fine_total:.2f} outstanding; {active_count} active loan(s).",
        "A copy is available to issue." if approved else "New borrowing is currently unavailable.",
    )
