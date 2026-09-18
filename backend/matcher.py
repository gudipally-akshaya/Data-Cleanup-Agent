# matcher.py
# ---------------------------------------------------------
# Compares two normalized customer records and decides:
#
# MERGE
# REVIEW
# KEEP_SEPARATE
#
# Safety principle:
# Strong matches increase confidence, but conflicting
# identity information prevents unsafe automatic merges.
# ---------------------------------------------------------

from rapidfuzz.fuzz import ratio


def similarity(value1, value2):
    """
    Returns similarity percentage between two values.
    """

    if not value1 or not value2:
        return 0

    return ratio(
        str(value1),
        str(value2)
    )


def values_conflict(value1, value2):
    """
    Returns True only when BOTH values exist
    and they are different.
    """

    return bool(
        value1
        and value2
        and value1 != value2
    )


def compare_records(record1, record2):
    """
    Compare two normalized customer records.

    Important:
    The numerical score is useful evidence,
    but safety rules determine the final decision.
    """

    # -----------------------------------------------------
    # NORMALIZED VALUES
    # -----------------------------------------------------

    name1 = record1.get("_norm_name", "")
    name2 = record2.get("_norm_name", "")

    email1 = record1.get("_norm_email", "")
    email2 = record2.get("_norm_email", "")

    phone1 = record1.get("_norm_phone", "")
    phone2 = record2.get("_norm_phone", "")

    address1 = record1.get("_norm_address", "")
    address2 = record2.get("_norm_address", "")

    city1 = record1.get("_norm_city", "")
    city2 = record2.get("_norm_city", "")

    # -----------------------------------------------------
    # FIELD SIMILARITY SCORES
    # -----------------------------------------------------

    name_score = similarity(
        name1,
        name2
    )

    email_score = similarity(
        email1,
        email2
    )

    phone_score = similarity(
        phone1,
        phone2
    )

    address_score = similarity(
        address1,
        address2
    )

    city_score = similarity(
        city1,
        city2
    )

    # -----------------------------------------------------
    # WEIGHTED CONFIDENCE SCORE
    # -----------------------------------------------------

    total_score = (
        name_score * 0.20
        + email_score * 0.35
        + phone_score * 0.30
        + address_score * 0.10
        + city_score * 0.05
    )

    # -----------------------------------------------------
    # EXACT MATCH SIGNALS
    # -----------------------------------------------------

    same_email = bool(
        email1
        and email2
        and email1 == email2
    )

    same_phone = bool(
        phone1
        and phone2
        and phone1 == phone2
    )

    same_city = bool(
        city1
        and city2
        and city1 == city2
    )

    # -----------------------------------------------------
    # CONFLICT SIGNALS
    # -----------------------------------------------------

    email_conflict = values_conflict(
        email1,
        email2
    )

    phone_conflict = values_conflict(
        phone1,
        phone2
    )

    address_conflict = (
        bool(address1 and address2)
        and address_score < 80
    )

    city_conflict = values_conflict(
        city1,
        city2
    )

    # -----------------------------------------------------
    # DECISION RULE 1
    #
    # Same email AND same phone gives very strong evidence.
    #
    # Example:
    # C1001 ↔ C1044
    # -----------------------------------------------------

    if (
        same_email
        and same_phone
        and name_score >= 70
    ):
        decision = "MERGE"

        reason = (
            "Email and phone match exactly, with "
            "supporting similarity in the customer information."
        )

    # -----------------------------------------------------
    # DECISION RULE 2
    #
    # Phone agrees, but email/address conflicts.
    #
    # Example:
    # C1001 ↔ C1088
    #
    # Do NOT automatically merge.
    # -----------------------------------------------------

    elif (
        same_phone
        and (
            email_conflict
            or address_conflict
        )
    ):
        decision = "REVIEW"

        reason = (
            "Phone matches, but other identifying information "
            "conflicts. Review is required before merging."
        )

    # -----------------------------------------------------
    # DECISION RULE 3
    #
    # Email agrees but phone conflicts.
    #
    # Example:
    # C3001 ↔ C3002
    # -----------------------------------------------------

    elif (
        same_email
        and phone_conflict
    ):
        decision = "REVIEW"

        reason = (
            "Email matches, but the phone numbers conflict. "
            "Manual or AI review is required before merging."
        )

    # -----------------------------------------------------
    # DECISION RULE 4
    #
    # Same/similar name but multiple identity fields differ.
    #
    # Example:
    # Rahul Kumar ↔ Rahul Kumar
    # -----------------------------------------------------

    elif (
        name_score >= 90
        and (
            email_conflict
            and phone_conflict
        )
    ):
        decision = "KEEP_SEPARATE"

        reason = (
            "Multiple identifying fields conflict. "
            "The records should remain separate."
        )

    # -----------------------------------------------------
    # DECISION RULE 5
    #
    # Different cities + conflicting contact details
    # provide additional evidence that these are
    # different customers.
    # -----------------------------------------------------

    elif (
        city_conflict
        and email_conflict
        and phone_conflict
    ):
        decision = "KEEP_SEPARATE"

        reason = (
            "The records contain conflicting contact "
            "and location information."
        )

    # -----------------------------------------------------
    # DECISION RULE 6
    #
    # Strong overall evidence without major conflicts.
    # -----------------------------------------------------

    elif (
        total_score >= 85
        and (
            same_email
            or same_phone
        )
        and not (
            email_conflict
            or phone_conflict
        )
    ):
        decision = "MERGE"

        reason = (
            "Strong identifying information matches "
            "with high overall similarity."
        )

    # -----------------------------------------------------
    # DECISION RULE 7
    #
    # Some evidence exists, but not enough for a
    # safe automatic decision.
    # -----------------------------------------------------

    elif total_score >= 60:
        decision = "REVIEW"

        reason = (
            "Some customer information matches, but "
            "the evidence is not strong enough for "
            "an automatic merge."
        )

    # -----------------------------------------------------
    # DECISION RULE 8
    #
    # Weak evidence.
    # -----------------------------------------------------

    else:
        decision = "KEEP_SEPARATE"

        reason = (
            "The records do not contain enough matching "
            "information to safely merge."
        )

    # -----------------------------------------------------
    # RETURN COMPLETE EXPLANATION
    # -----------------------------------------------------

    return {
        "score": round(
            total_score,
            2
        ),

        "decision": decision,

        "reason": reason,

        "field_scores": {
            "name": round(name_score, 2),
            "email": round(email_score, 2),
            "phone": round(phone_score, 2),
            "address": round(address_score, 2),
            "city": round(city_score, 2),
        },

        "conflict_flags": {
            "email_conflict": email_conflict,
            "phone_conflict": phone_conflict,
            "address_conflict": address_conflict,
            "city_conflict": city_conflict,
        }
    }