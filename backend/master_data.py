# master_data.py
# ---------------------------------------------------------
# Creates the final clean master customer dataset.
#
# Safety rules:
# - MERGE only records approved by the matcher.
# - REVIEW records are NOT automatically merged.
# - KEEP_SEPARATE records remain independent.
# - Missing values are recovered from related records.
# - True conflicting values are preserved for auditability.
# - Formatting differences are NOT treated as conflicts.
# ---------------------------------------------------------

import re
import pandas as pd


# ---------------------------------------------------------
# HELPER: CHECK IF VALUE IS MISSING
# ---------------------------------------------------------

def is_missing(value):
    """
    Returns True when a value is empty or NaN.
    """

    return (
        pd.isna(value)
        or str(value).strip() == ""
    )


# ---------------------------------------------------------
# HELPER: CLEAN VALUE FOR DISPLAY
# ---------------------------------------------------------

def display_value(value):
    """
    Converts a value into a clean string for
    conflict reporting.
    """

    if is_missing(value):
        return ""

    return str(value).strip()


# ---------------------------------------------------------
# NORMALIZATION HELPERS FOR CONFLICT DETECTION
# ---------------------------------------------------------

def normalize_basic(value):
    """
    General text normalization.

    Example:
        ' Hyderabad ' -> 'hyderabad'
    """

    if is_missing(value):
        return ""

    value = str(value).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def normalize_phone_for_conflict(value):
    """
    Phone numbers are compared using digits only.

    Example:
        '+91 98765-43210'
        '91 9876543210'

    become equivalent digit strings.
    """

    if is_missing(value):
        return ""

    return re.sub(
        r"\D",
        "",
        str(value)
    )


def normalize_address_for_conflict(value):
    """
    Normalizes common address abbreviations so
    formatting differences are not conflicts.

    Examples:

        12 Lake Road
        12 Lake Rd

    both become:

        12 lake rd
    """

    value = normalize_basic(
        value
    )

    if not value:
        return ""

    replacements = {
        r"\broad\b": "rd",
        r"\brd\.\b": "rd",

        r"\bstreet\b": "st",
        r"\bst\.\b": "st",

        r"\bavenue\b": "ave",
        r"\bave\.\b": "ave",

        r"\blane\b": "ln",
        r"\bln\.\b": "ln",

        r"\bdrive\b": "dr",
        r"\bdr\.\b": "dr",

        r"\bboulevard\b": "blvd",
        r"\bblvd\.\b": "blvd",
    }

    for pattern, replacement in replacements.items():

        value = re.sub(
            pattern,
            replacement,
            value
        )

    # Remove punctuation that does not affect identity.
    value = re.sub(
        r"[,.]",
        "",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_email_for_conflict(value):
    """
    Email comparison is case-insensitive and
    ignores surrounding spaces.
    """

    if is_missing(value):
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def normalize_name_for_conflict(value):
    """
    Performs conservative name normalization.

    We normalize spaces, case and punctuation.

    IMPORTANT:
    We do NOT automatically treat initials as
    equivalent to full names here.

    Example:
        S. Srirampur
        Sneha Srirampur

    may still be reported as a name variation.
    That is safer than assuming an initial always
    represents a particular full name.
    """

    value = normalize_basic(
        value
    )

    if not value:
        return ""

    # Remove periods after initials.
    value = value.replace(
        ".",
        ""
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_for_conflict(column, value):
    """
    Select the correct normalization rule for
    each customer field.
    """

    if column == "email":

        return normalize_email_for_conflict(
            value
        )

    if column == "phone":

        return normalize_phone_for_conflict(
            value
        )

    if column == "address":

        return normalize_address_for_conflict(
            value
        )

    if column == "name":

        return normalize_name_for_conflict(
            value
        )

    if column == "city":

        return normalize_basic(
            value
        )

    return normalize_basic(
        value
    )


# ---------------------------------------------------------
# GET UNIQUE SEMANTIC VALUES
# ---------------------------------------------------------

def get_unique_values(group, column):
    """
    Finds unique values using normalized comparison,
    while preserving the original values for display.

    Example:

        "12 Lake Road"
        "12 Lake Rd"

    have the same normalized representation,
    therefore they count as ONE value.
    """

    normalized_seen = {}

    for _, row in group.iterrows():

        value = row.get(
            column
        )

        if is_missing(value):
            continue

        original_value = display_value(
            value
        )

        normalized_value = (
            normalize_for_conflict(
                column,
                value
            )
        )

        if not normalized_value:
            continue

        # Store only the first original representation
        # of each normalized value.
        if normalized_value not in normalized_seen:

            normalized_seen[
                normalized_value
            ] = original_value

    return list(
        normalized_seen.values()
    )


# ---------------------------------------------------------
# CHOOSE MASTER RECORD
# ---------------------------------------------------------

def choose_master_record(group):
    """
    Creates one safe master record from a duplicate group.

    Strategy:

    1. Sort by last_updated.
    2. Use newest record as the base.
    3. Fill missing values from older records.
    4. Compare normalized values for conflicts.
    5. Preserve TRUE conflicts in the audit output.

    Returns:
        master_record
        conflicts
    """

    group = group.copy()


    # -----------------------------------------------------
    # STEP 1
    # CHOOSE NEWEST RECORD
    # -----------------------------------------------------

    if "last_updated" in group.columns:

        group["_parsed_date"] = (
            pd.to_datetime(
                group["last_updated"],
                errors="coerce"
            )
        )

        group = group.sort_values(
            "_parsed_date",
            ascending=False,
            na_position="last"
        )


    # Newest record becomes the base.
    master = group.iloc[0].copy()

    conflicts = {}


    # -----------------------------------------------------
    # Fields where conflicting values matter.
    # -----------------------------------------------------

    conflict_columns = [
        "name",
        "email",
        "phone",
        "address",
        "city"
    ]


    # -----------------------------------------------------
    # STEP 2
    # PROCESS ALL FIELDS
    # -----------------------------------------------------

    for column in group.columns:

        # Ignore helper/internal columns.
        if str(column).startswith("_"):
            continue

        # customer_id is tracked separately using
        # merged_from.
        if column == "customer_id":
            continue

        current_value = master.get(
            column
        )


        # -------------------------------------------------
        # STEP 2A
        # FILL MISSING MASTER VALUES
        # -------------------------------------------------

        if is_missing(
            current_value
        ):

            for _, row in group.iterrows():

                candidate_value = row.get(
                    column
                )

                if not is_missing(
                    candidate_value
                ):

                    master[column] = (
                        candidate_value
                    )

                    current_value = (
                        candidate_value
                    )

                    break


        # -------------------------------------------------
        # STEP 2B
        # DETECT TRUE CONFLICTS
        # -------------------------------------------------

        if column in conflict_columns:

            unique_values = (
                get_unique_values(
                    group,
                    column
                )
            )

            # Only multiple SEMANTICALLY different
            # values count as a conflict.
            if len(unique_values) > 1:

                conflicts[
                    column
                ] = unique_values


    return master, conflicts


# ---------------------------------------------------------
# BUILD MASTER DATASET
# ---------------------------------------------------------

def build_master_dataset(
    df,
    candidates
):
    """
    Builds the clean master dataset.

    MERGE:
        Records join the same master group.

    REVIEW:
        Records remain separate until resolved.

    KEEP_SEPARATE:
        Records remain independent.

    Connected MERGE relationships are handled
    consistently using Union-Find.
    """

    df = df.copy()


    # -----------------------------------------------------
    # UNION-FIND SETUP
    # -----------------------------------------------------

    parent = {}

    customer_ids = []


    for index, row in df.iterrows():

        customer_id = str(
            row.get(
                "customer_id",
                f"ROW_{index + 1}"
            )
        )

        customer_ids.append(
            customer_id
        )

        parent[
            customer_id
        ] = customer_id


    # -----------------------------------------------------
    # FIND
    # -----------------------------------------------------

    def find(customer_id):

        if (
            parent[customer_id]
            != customer_id
        ):

            parent[customer_id] = find(
                parent[customer_id]
            )

        return parent[
            customer_id
        ]


    # -----------------------------------------------------
    # UNION
    # -----------------------------------------------------

    def union(id1, id2):

        root1 = find(
            id1
        )

        root2 = find(
            id2
        )

        if root1 != root2:

            parent[
                root2
            ] = root1


    # -----------------------------------------------------
    # ONLY MERGE DECISIONS CREATE GROUPS
    # -----------------------------------------------------

    for candidate in candidates:

        if (
            candidate.get(
                "decision"
            )
            == "MERGE"
        ):

            id1 = str(
                candidate[
                    "record_1_id"
                ]
            )

            id2 = str(
                candidate[
                    "record_2_id"
                ]
            )

            if (
                id1 in parent
                and id2 in parent
            ):

                union(
                    id1,
                    id2
                )


    # -----------------------------------------------------
    # BUILD GROUPS
    # -----------------------------------------------------

    groups = {}

    for customer_id in customer_ids:

        root = find(
            customer_id
        )

        if root not in groups:

            groups[root] = []

        groups[root].append(
            customer_id
        )


    # -----------------------------------------------------
    # CREATE MASTER RECORDS
    # -----------------------------------------------------

    master_records = []


    for _, ids in groups.items():

        group_df = df[
            df["customer_id"]
            .astype(str)
            .isin(ids)
        ].copy()


        # -------------------------------------------------
        # CREATE SAFE MASTER
        # -------------------------------------------------

        master, conflicts = (
            choose_master_record(
                group_df
            )
        )


        # -------------------------------------------------
        # TRACK SOURCE RECORD IDS
        # -------------------------------------------------

        master[
            "merged_from"
        ] = ", ".join(
            ids
        )


        # -------------------------------------------------
        # BUILD CONFLICT MESSAGE
        # -------------------------------------------------

        if conflicts:

            conflict_messages = []

            for (
                field,
                values
            ) in conflicts.items():

                conflict_messages.append(
                    f"{field}: "
                    f"{' | '.join(values)}"
                )

            master[
                "conflicts"
            ] = "; ".join(
                conflict_messages
            )

        else:

            master[
                "conflicts"
            ] = ""


        # -------------------------------------------------
        # REMOVE INTERNAL FIELDS
        # -------------------------------------------------

        master = master[
            [
                column

                for column
                in master.index

                if not str(
                    column
                ).startswith("_")
            ]
        ]


        master_records.append(
            master.to_dict()
        )


    # -----------------------------------------------------
    # FINAL DATAFRAME
    # -----------------------------------------------------

    master_df = pd.DataFrame(
        master_records
    )

    master_df = (
        master_df.fillna("")
    )

    return master_df