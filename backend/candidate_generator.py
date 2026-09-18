# candidate_generator.py
# ---------------------------------------------------------
# Generates realistic duplicate candidate pairs.
#
# IMPORTANT:
# We do NOT compare every customer with every other customer.
# A pair becomes a candidate only when there is meaningful
# evidence that the two records could represent the same person.
# ---------------------------------------------------------

from rapidfuzz.fuzz import ratio


def generate_candidate_pairs(records):
    """
    Return a list of (i, j) candidate record indexes.

    A pair becomes a candidate when at least one useful
    identity signal is present:
      1. Same email
      2. Same phone
      3. Very similar name
    """

    candidate_pairs = []

    for i in range(len(records)):

        for j in range(i + 1, len(records)):

            record1 = records[i]
            record2 = records[j]

            name1 = record1.get("_norm_name", "")
            name2 = record2.get("_norm_name", "")

            email1 = record1.get("_norm_email", "")
            email2 = record2.get("_norm_email", "")

            phone1 = record1.get("_norm_phone", "")
            phone2 = record2.get("_norm_phone", "")

            # ---------------------------------------------
            # SIGNAL 1: Exact email match
            # ---------------------------------------------

            same_email = (
                email1 != ""
                and email2 != ""
                and email1 == email2
            )

            # ---------------------------------------------
            # SIGNAL 2: Exact phone match
            # ---------------------------------------------

            same_phone = (
                phone1 != ""
                and phone2 != ""
                and phone1 == phone2
            )

            # ---------------------------------------------
            # SIGNAL 3: Highly similar customer name
            # ---------------------------------------------

            name_similarity = 0

            if name1 and name2:
                name_similarity = ratio(name1, name2)

            similar_name = name_similarity >= 80

            # ---------------------------------------------
            # Candidate rule
            # ---------------------------------------------
            # We include the pair if ANY meaningful identity
            # signal suggests that it deserves investigation.
            #
            # This keeps:
            # Sneha variants
            # Rahul same-name test
            # Anita conflicting-phone test
            #
            # But removes unrelated combinations.
            # ---------------------------------------------

            if same_email or same_phone or similar_name:

                candidate_pairs.append(
                    (i, j)
                )

    return candidate_pairs