# cleanup.py
# ---------------------------------------------------------
# Functions for cleaning and normalizing customer data.
# ---------------------------------------------------------

import re
import pandas as pd


def clean_text(value):
    """
    Converts a value to lowercase text and removes
    unnecessary spaces.
    """
    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def normalize_name(name):
    """
    Example:
    '  Sneha Srirampur ' -> 'sneha srirampur'
    """
    name = clean_text(name)

    # Replace multiple spaces with one space
    name = re.sub(r"\s+", " ", name)

    return name


def normalize_email(email):
    """
    Example:
    ' SNEHA@GMAIL.COM ' -> 'sneha@gmail.com'
    """
    return clean_text(email)


def normalize_phone(phone):
    """
    Keeps only digits.

    Example:
    '+91 98765-43210' -> '919876543210'
    """
    if pd.isna(phone):
        return ""

    return re.sub(r"\D", "", str(phone))


def normalize_address(address):
    """
    Standardizes common address words.

    Example:
    '12 Lake Road' -> '12 lake rd'
    '22 Park Street' -> '22 park st'
    """
    address = clean_text(address)

    replacements = {
        r"\broad\b": "rd",
        r"\bstreet\b": "st",
        r"\bavenue\b": "ave",
        r"\blane\b": "ln",
    }

    for old, new in replacements.items():
        address = re.sub(old, new, address)

    address = re.sub(r"\s+", " ", address)

    return address


def normalize_city(city):
    """
    Example:
    ' Hyderabad ' -> 'hyderabad'
    """
    return clean_text(city)


def normalize_dataframe(df):
    """
    Creates normalized versions of important customer fields.

    Original columns are NOT removed.
    """

    df = df.copy()

    if "name" in df.columns:
        df["_norm_name"] = df["name"].apply(normalize_name)

    if "email" in df.columns:
        df["_norm_email"] = df["email"].apply(normalize_email)

    if "phone" in df.columns:
        df["_norm_phone"] = df["phone"].apply(normalize_phone)

    if "address" in df.columns:
        df["_norm_address"] = df["address"].apply(normalize_address)

    if "city" in df.columns:
        df["_norm_city"] = df["city"].apply(normalize_city)

    return df