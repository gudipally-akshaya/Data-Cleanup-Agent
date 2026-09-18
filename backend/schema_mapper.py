# schema_mapper.py
# ---------------------------------------------------------
# Maps common external customer-dataset column names
# to the standard schema used by the Data Cleanup Agent.
# ---------------------------------------------------------

import re


# Standard fields understood by our cleanup agent.
COLUMN_ALIASES = {

    "customer_id": [
        "customer_id",
        "customerid",
        "customer id",
        "cust_id",
        "custid",
        "client_id",
        "clientid",
        "client id",
        "record_id",
        "recordid",
        "record id",
        "id",
    ],

    "name": [
        "name",
        "full_name",
        "fullname",
        "full name",
        "customer_name",
        "customername",
        "customer name",
        "client_name",
        "clientname",
        "client name",
    ],

    "email": [
        "email",
        "email_address",
        "emailaddress",
        "email address",
        "e_mail",
        "e-mail",
        "mail",
    ],

    "phone": [
        "phone",
        "phone_number",
        "phonenumber",
        "phone number",
        "mobile",
        "mobile_number",
        "mobilenumber",
        "mobile number",
        "contact",
        "contact_number",
        "contactnumber",
        "contact number",
        "telephone",
        "tel",
    ],

    "address": [
        "address",
        "street_address",
        "streetaddress",
        "street address",
        "customer_address",
        "customeraddress",
        "customer address",
        "residential_address",
        "residential address",
        "location",
    ],

    "city": [
        "city",
        "town",
        "customer_city",
        "customer city",
        "location_city",
        "location city",
    ],

    "last_updated": [
        "last_updated",
        "lastupdated",
        "last updated",
        "updated_at",
        "updatedat",
        "updated at",
        "modified_at",
        "modifiedat",
        "modified at",
        "modified_date",
        "modified date",
        "update_date",
        "update date",
        "last_modified",
        "last modified",
    ],

    "source": [
        "source",
        "data_source",
        "datasource",
        "data source",
        "channel",
        "origin",
        "system",
        "source_system",
        "source system",
    ],
}


def normalize_column_name(column):
    """
    Convert a column name into a simple comparable form.

    Examples:

        "Full Name"     -> "full name"
        "FULL_NAME"     -> "full name"
        "Mobile-Number" -> "mobile number"
    """

    column = str(column).strip().lower()

    # Convert separators to spaces.
    column = re.sub(r"[_\-]+", " ", column)

    # Remove unnecessary punctuation.
    column = re.sub(r"[^\w\s]", "", column)

    # Remove repeated spaces.
    column = re.sub(r"\s+", " ", column)

    return column.strip()


def build_alias_lookup():
    """
    Build:

        normalized alias -> standard column

    Example:

        "mobile number" -> "phone"
        "full name"     -> "name"
    """

    lookup = {}

    for standard_column, aliases in COLUMN_ALIASES.items():

        # Include the standard name itself.
        all_aliases = aliases + [standard_column]

        for alias in all_aliases:

            normalized_alias = normalize_column_name(alias)

            lookup[normalized_alias] = standard_column

    return lookup


ALIAS_LOOKUP = build_alias_lookup()


def map_external_schema(df):
    """
    Maps external customer column names to our
    standard Data Cleanup Agent schema.

    Returns:

        mapped_dataframe
        mapping_report

    Example mapping report:

        {
            "Customer ID": "customer_id",
            "Full Name": "name",
            "Mobile Number": "phone"
        }
    """

    df = df.copy()

    rename_map = {}

    used_standard_columns = set()

    for original_column in df.columns:

        normalized_column = normalize_column_name(
            original_column
        )

        standard_column = ALIAS_LOOKUP.get(
            normalized_column
        )

        # Only map if:
        # 1. We recognize the column.
        # 2. Another external column has not already
        #    been mapped to the same standard field.
        if (
            standard_column
            and standard_column not in used_standard_columns
        ):

            rename_map[original_column] = standard_column

            used_standard_columns.add(
                standard_column
            )

    df = df.rename(columns=rename_map)

    # -----------------------------------------------------
    # CUSTOMER ID FALLBACK
    # -----------------------------------------------------
    # Some external datasets may not contain an ID.
    # Generate a safe temporary ID so the rest of the
    # cleanup pipeline can still operate.
    # -----------------------------------------------------

    if "customer_id" not in df.columns:

        df["customer_id"] = [
            f"ROW_{index + 1}"
            for index in range(len(df))
        ]

    return df, rename_map