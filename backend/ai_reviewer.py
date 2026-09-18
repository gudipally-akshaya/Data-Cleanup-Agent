# ai_reviewer.py
# ---------------------------------------------------------
# AI Review Layer
#
# Only ambiguous records marked REVIEW are sent here.
#
# For now this uses an explainable conservative reviewer.
# Later we can connect an actual LLM API without changing
# the rest of our application.
# ---------------------------------------------------------


def review_ambiguous_pair(record1, record2, comparison):
    """
    Investigates an ambiguous duplicate candidate.

    Returns:
        ai_decision
        ai_reason
        requires_human_review
    """

    email1 = record1.get("_norm_email", "")
    email2 = record2.get("_norm_email", "")

    phone1 = record1.get("_norm_phone", "")
    phone2 = record2.get("_norm_phone", "")

    name1 = record1.get("_norm_name", "")
    name2 = record2.get("_norm_name", "")

    address1 = record1.get("_norm_address", "")
    address2 = record2.get("_norm_address", "")

    # -----------------------------------------------------
    # Detect important evidence
    # -----------------------------------------------------

    same_email = (
        email1
        and email2
        and email1 == email2
    )

    same_phone = (
        phone1
        and phone2
        and phone1 == phone2
    )

    phone_conflict = (
        phone1
        and phone2
        and phone1 != phone2
    )

    same_name = (
        name1
        and name2
        and name1 == name2
    )

    same_address = (
        address1
        and address2
        and address1 == address2
    )

    # -----------------------------------------------------
    # Conservative investigation
    # -----------------------------------------------------

    # Example:
    # Anita has the same email/name/address,
    # but different phone numbers.
    #
    # We should NOT automatically merge because there is
    # conflicting identifying information.
    if same_email and phone_conflict:

        return {
            "ai_decision": "NEEDS_HUMAN_REVIEW",
            "ai_reason": (
                "The records share the same email"
                " but contain conflicting phone numbers. "
                "Because a strong identity field conflicts, "
                "an automatic merge may be unsafe."
            ),
            "requires_human_review": True
        }

    # Strong agreement across several identity fields.
    if (
        same_email
        and same_phone
        and (same_name or same_address)
    ):

        return {
            "ai_decision": "MERGE",
            "ai_reason": (
                "Multiple strong identity fields agree, "
                "including email and phone."
            ),
            "requires_human_review": False
        }

    # Not enough evidence.
    return {
        "ai_decision": "NEEDS_HUMAN_REVIEW",
        "ai_reason": (
            "The available evidence is ambiguous. "
            "The agent cannot safely determine that both "
            "records represent the same customer."
        ),
        "requires_human_review": True
    }