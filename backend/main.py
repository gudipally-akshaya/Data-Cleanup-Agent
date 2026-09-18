# main.py
# ---------------------------------------------------------
# DATA CLEANUP AGENT - FASTAPI BACKEND
#
# Features:
# - CSV / JSON / XLSX upload
# - Natural-language cleanup instruction
# - Normalization
# - Deterministic duplicate candidate generation
# - Similarity + conflict checking
# - AI investigation only for ambiguous cases
# - Human review
# - Safe merge validation
# - Missing-value handling
# - Clean master dataset generation
# - Data Quality Report
# - Automatic vs Human-approved merge tracking
# - CSV / XLSX / Decision Log exports
# ---------------------------------------------------------

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

import pandas as pd
import numpy as np
import io
import math

from datetime import date, datetime

from cleanup import normalize_dataframe
from matcher import compare_records
from master_data import build_master_dataset
from candidate_generator import generate_candidate_pairs
from ai_reviewer import review_ambiguous_pair
from schema_mapper import map_external_schema


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Data Cleanup Agent API",
    description="Safe customer data cleanup and deduplication agent.",
    version="1.3"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class ApplyDecisionsRequest(BaseModel):
    records: list[dict]
    candidates: list[dict]
    manual_decisions: dict[str, str]


class ExportRequest(BaseModel):
    master_data: list[dict]
    candidates: list[dict] = []


# =========================================================
# JSON SAFE CONVERSION
# =========================================================

def make_json_safe(value):
    """
    Converts pandas / NumPy values into values that
    standard JSON can safely serialize.

    Examples:

        NaN       -> None
        pd.NA     -> None
        NaT       -> None
        Timestamp -> ISO string
        NumPy int -> Python int
        NumPy float -> Python float
    """

    # Dictionary
    if isinstance(value, dict):

        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    # List / tuple / set
    if isinstance(value, (list, tuple, set)):

        return [
            make_json_safe(item)
            for item in value
        ]

    # Date / datetime
    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date
        )
    ):

        if pd.isna(value):
            return None

        return value.isoformat()

    # NumPy integer
    if isinstance(value, np.integer):
        return int(value)

    # NumPy floating point
    if isinstance(value, np.floating):

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    # Normal Python float
    if isinstance(value, float):

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    # Other pandas missing values
    try:

        missing = pd.isna(value)

        if isinstance(
            missing,
            (bool, np.bool_)
        ) and missing:

            return None

    except (TypeError, ValueError):
        pass

    return value


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Data Cleanup Agent API is running!",
        "status": "success",
        "version": "1.3"
    }


# =========================================================
# READ DATASET
# =========================================================

async def read_dataset(file: UploadFile):

    filename = (
        file.filename or ""
    ).lower()

    contents = await file.read()

    try:

        # CSV
        if filename.endswith(".csv"):

            df = pd.read_csv(
                io.BytesIO(contents)
            )

        # JSON
        elif filename.endswith(".json"):

            df = pd.read_json(
                io.BytesIO(contents)
            )

        # Excel
        elif filename.endswith(".xlsx"):

            df = pd.read_excel(
                io.BytesIO(contents),
                engine="openpyxl"
            )

        else:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type. "
                    "Please upload CSV, JSON or XLSX."
                )
            )

        return df

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Could not read dataset: {str(error)}"
        )


# =========================================================
# DATA QUALITY REPORT
# =========================================================

def create_data_quality_report(
    df,
    candidates,
    master_df
):
    """
    Creates the live Data Quality Report.

    Important:

    Automatic merges and human-approved merges are
    counted separately.

    A candidate is an automatic merge only when:

        decision == MERGE
        decision_source != HUMAN

    A candidate is a human-approved merge when:

        decision == MERGE
        decision_source == HUMAN
    """

    important_columns = [
        "name",
        "email",
        "phone",
        "address",
        "city"
    ]

    available_columns = [
        column
        for column in important_columns
        if column in df.columns
    ]

    # -----------------------------------------------------
    # MISSING VALUES
    # -----------------------------------------------------

    missing_values = 0
    missing_by_field = {}

    for column in available_columns:

        series = df[column]

        missing_mask = (
            series.isna()
            |
            series
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )

        missing_count = int(
            missing_mask.sum()
        )

        missing_values += missing_count

        missing_by_field[column] = (
            missing_count
        )

    # -----------------------------------------------------
    # AUTOMATIC MERGES
    # -----------------------------------------------------

    automatic_merges = sum(
        1
        for candidate in candidates
        if (
            candidate.get("decision") == "MERGE"
            and
            candidate.get(
                "decision_source",
                "AUTOMATIC"
            ) != "HUMAN"
        )
    )

    # -----------------------------------------------------
    # HUMAN APPROVED MERGES
    # -----------------------------------------------------

    human_approved_merges = sum(
        1
        for candidate in candidates
        if (
            candidate.get("decision") == "MERGE"
            and
            candidate.get("decision_source") == "HUMAN"
        )
    )

    # -----------------------------------------------------
    # TOTAL MERGE DECISIONS
    # -----------------------------------------------------

    total_merges = (
        automatic_merges
        +
        human_approved_merges
    )

    # -----------------------------------------------------
    # UNRESOLVED REVIEW CASES
    # -----------------------------------------------------

    review_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision") == "REVIEW"
    )

    # -----------------------------------------------------
    # KEEP SEPARATE
    # -----------------------------------------------------

    separate_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision") == "KEEP_SEPARATE"
    )

    # -----------------------------------------------------
    # HUMAN KEEP-SEPARATE DECISIONS
    # -----------------------------------------------------

    human_keep_separate = sum(
        1
        for candidate in candidates
        if (
            candidate.get("decision") == "KEEP_SEPARATE"
            and
            candidate.get("decision_source") == "HUMAN"
        )
    )

    # -----------------------------------------------------
    # TOTAL HUMAN DECISIONS
    # -----------------------------------------------------

    human_decisions = sum(
        1
        for candidate in candidates
        if candidate.get("decision_source") == "HUMAN"
    )

    # -----------------------------------------------------
    # MASTER CONFLICT COUNT
    # -----------------------------------------------------

    conflict_count = 0

    if "conflicts" in master_df.columns:

        conflict_count = int(
            master_df["conflicts"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )

    # -----------------------------------------------------
    # RECORDS CONSOLIDATED
    # -----------------------------------------------------

    records_consolidated = max(
        0,
        len(df) - len(master_df)
    )

    # -----------------------------------------------------
    # DATA QUALITY STATUS
    # -----------------------------------------------------

    if review_count > 0:

        status = "REVIEW_RECOMMENDED"

        status_message = (
            f"{review_count} ambiguous candidate pair"
            f"{'s' if review_count != 1 else ''} "
            "still require review before the dataset "
            "is fully resolved."
        )

    elif conflict_count > 0:

        status = "CONFLICTS_PRESERVED"

        status_message = (
            "All duplicate decisions are resolved, "
            "but some merged records contain preserved "
            "field variations or conflicts."
        )

    elif missing_values > 0:

        status = "MISSING_DATA"

        status_message = (
            "Duplicate decisions are resolved, but some "
            "customer fields still contain missing values."
        )

    else:

        status = "CLEAN"

        status_message = (
            "No unresolved duplicate candidates, "
            "missing values, or master-record conflicts remain."
        )

    return {

        "missing_values":
            missing_values,

        "missing_by_field":
            missing_by_field,

        "duplicate_candidates":
            len(candidates),

        "conflicts_detected":
            conflict_count,

        # Backward-compatible key.
        "auto_merges":
            automatic_merges,

        # Clearer new key.
        "automatic_merges":
            automatic_merges,

        "human_approved_merges":
            human_approved_merges,

        "total_merges":
            total_merges,

        "needs_human_review":
            review_count,

        "keep_separate":
            separate_count,

        "human_keep_separate":
            human_keep_separate,

        "human_decisions":
            human_decisions,

        "records_consolidated":
            records_consolidated,

        "original_records":
            len(df),

        "clean_master_records":
            len(master_df),

        "status":
            status,

        "status_message":
            status_message
    }


# =========================================================
# SAFE MERGE VALIDATION
# =========================================================

def validate_safe_merge_graph(candidates):
    """
    Prevents unsafe transitive merges.

    Example:

        A MERGE B
        B MERGE C

    means A, B and C become one customer.

    If another candidate relationship inside that
    connected group is REVIEW or KEEP_SEPARATE,
    the merge is blocked.
    """

    ids = set()

    for candidate in candidates:

        ids.add(
            str(candidate["record_1_id"])
        )

        ids.add(
            str(candidate["record_2_id"])
        )

    parent = {
        customer_id: customer_id
        for customer_id in ids
    }

    # -----------------------------------------------------
    # FIND
    # -----------------------------------------------------

    def find(customer_id):

        if parent[customer_id] != customer_id:

            parent[customer_id] = find(
                parent[customer_id]
            )

        return parent[customer_id]

    # -----------------------------------------------------
    # UNION
    # -----------------------------------------------------

    def union(id1, id2):

        root1 = find(id1)
        root2 = find(id2)

        if root1 != root2:
            parent[root2] = root1

    # -----------------------------------------------------
    # BUILD MERGE GRAPH
    # -----------------------------------------------------

    for candidate in candidates:

        if candidate.get("decision") == "MERGE":

            id1 = str(
                candidate["record_1_id"]
            )

            id2 = str(
                candidate["record_2_id"]
            )

            union(
                id1,
                id2
            )

    # -----------------------------------------------------
    # CHECK NON-MERGE RELATIONSHIPS
    # -----------------------------------------------------

    for candidate in candidates:

        decision = candidate.get(
            "decision"
        )

        if decision == "MERGE":
            continue

        id1 = str(
            candidate["record_1_id"]
        )

        id2 = str(
            candidate["record_2_id"]
        )

        if find(id1) == find(id2):

            # Explicit separate relationship
            if decision == "KEEP_SEPARATE":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Unsafe merge blocked. "
                        f"{id1} and {id2} are marked "
                        "KEEP_SEPARATE, but this merge "
                        "would indirectly place them in "
                        "the same master customer group."
                    )
                )

            # Still unresolved
            if decision == "REVIEW":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Merge requires additional review. "
                        f"{id1} and {id2} are still marked "
                        "REVIEW, but this merge would "
                        "indirectly place them in the same "
                        "master customer group. Resolve all "
                        "connected ambiguous relationships "
                        "before completing this merge."
                    )
                )


# =========================================================
# ANALYZE DATASET
# =========================================================

@app.post("/analyze")
async def analyze_dataset(
    file: UploadFile = File(...),

    instruction: str = Form(
        "Find duplicate customer records. "
        "Merge only when confident; "
        "flag uncertain cases."
    )
):

    # -----------------------------------------------------
    # READ DATASET
    # -----------------------------------------------------

    df = await read_dataset(file)

    if df.empty:

        raise HTTPException(
            status_code=400,
            detail="The uploaded dataset is empty."
        )

    # -----------------------------------------------------
    # MAP EXTERNAL DATASET COLUMN NAMES
    # -----------------------------------------------------

    # Example:
    # "Full Name"     -> "name"
    # "Mobile Number" -> "phone"
    # "Email Address" -> "email"

    df, schema_mapping = map_external_schema(df)


    # -----------------------------------------------------
    # VALIDATE USEFUL FIELDS
    # -----------------------------------------------------

    useful_fields = {
        "name",
        "email",
        "phone",
        "address",
        "city"
    }

    if not useful_fields.intersection(
        set(df.columns)
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Dataset must contain at least one of "
                "these columns: name, email, phone, "
                "address, city."
            )
        )

    # -----------------------------------------------------
    # NORMALIZE CUSTOMER DATA
    # -----------------------------------------------------

    normalized_df = normalize_dataframe(
        df
    )

    # -----------------------------------------------------
    # JSON-SAFE RECORDS
    # -----------------------------------------------------

    records = make_json_safe(
        normalized_df.to_dict(
            orient="records"
        )
    )

    # -----------------------------------------------------
    # GENERATE CANDIDATE PAIRS
    # -----------------------------------------------------

    candidate_pairs = (
        generate_candidate_pairs(
            records
        )
    )

    candidates = []

    # -----------------------------------------------------
    # PROCESS CANDIDATES
    # -----------------------------------------------------

    for i, j in candidate_pairs:

        record1 = records[i]
        record2 = records[j]

        comparison = compare_records(
            record1,
            record2
        )

        # -------------------------------------------------
        # AI ONLY FOR AMBIGUOUS CASES
        # -------------------------------------------------

        ai_review = None

        if comparison["decision"] == "REVIEW":

            ai_review = review_ambiguous_pair(
                record1,
                record2,
                comparison
            )

        # -------------------------------------------------
        # CREATE CANDIDATE
        # -------------------------------------------------

        candidate = {

            "record_1_id": str(
                record1.get(
                    "customer_id",
                    f"ROW_{i + 1}"
                )
            ),

            "record_2_id": str(
                record2.get(
                    "customer_id",
                    f"ROW_{j + 1}"
                )
            ),

            "score":
                comparison["score"],

            "decision":
                comparison["decision"],

            "original_decision":
                comparison["decision"],

            "reason":
                comparison["reason"],

            "decision_source":
                "AUTOMATIC",

            "ai_review":
                ai_review,

            "field_scores":
                comparison["field_scores"],

            "conflict_flags":
                comparison.get(
                    "conflict_flags",
                    {}
                ),

            "record_1": {
                key: value
                for key, value in record1.items()
                if not str(key).startswith("_norm_")
            },

            "record_2": {
                key: value
                for key, value in record2.items()
                if not str(key).startswith("_norm_")
            }
        }

        candidates.append(
            make_json_safe(
                candidate
            )
        )

    # Highest confidence first
    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # -----------------------------------------------------
    # BUILD MASTER DATASET
    # -----------------------------------------------------

    master_df = build_master_dataset(
        df,
        candidates
    )

    # -----------------------------------------------------
    # QUALITY REPORT
    # -----------------------------------------------------

    data_quality_report = (
        create_data_quality_report(
            df,
            candidates,
            master_df
        )
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    merge_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision") == "MERGE"
    )

    review_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision") == "REVIEW"
    )

    separate_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision") == "KEEP_SEPARATE"
    )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    response = {

        "success":
            True,

        "filename":
            file.filename,

        "instruction":
            instruction,

        "total_records":
            len(df),

        "columns":
            list(df.columns),

        "summary": {

            "candidate_pairs":
                len(candidates),

            "merge":
                merge_count,

            "review":
                review_count,

            "keep_separate":
                separate_count
        },

        "data_quality_report":
            data_quality_report,

        "preview":
            make_json_safe(
                df.to_dict(
                    orient="records"
                )
            ),

        "master_record_count":
            len(master_df),

        "master_data":
            make_json_safe(
                master_df.to_dict(
                    orient="records"
                )
            ),

        "candidates":
            candidates
    }

    return make_json_safe(
        response
    )


# =========================================================
# APPLY HUMAN DECISIONS
# =========================================================

@app.post("/apply-decisions")
def apply_decisions(
    request: ApplyDecisionsRequest
):

    allowed_decisions = {
        "MERGE",
        "KEEP_SEPARATE"
    }

    # -----------------------------------------------------
    # VALIDATE HUMAN DECISIONS
    # -----------------------------------------------------

    for pair_key, decision in (
        request.manual_decisions.items()
    ):

        if decision not in allowed_decisions:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid manual decision for "
                    f"{pair_key}: {decision}"
                )
            )

    updated_candidates = []

    # -----------------------------------------------------
    # APPLY HUMAN DECISIONS
    # -----------------------------------------------------

    for candidate in request.candidates:

        updated_candidate = (
            candidate.copy()
        )

        id1 = str(
            candidate["record_1_id"]
        )

        id2 = str(
            candidate["record_2_id"]
        )

        pair_key = (
            f"{id1}-{id2}"
        )

        reverse_pair_key = (
            f"{id2}-{id1}"
        )

        manual_decision = (
            request.manual_decisions.get(
                pair_key
            )
            or
            request.manual_decisions.get(
                reverse_pair_key
            )
        )

        original_decision = (
            candidate.get(
                "original_decision",
                candidate.get("decision")
            )
        )

        # -------------------------------------------------
        # ONLY ORIGINAL REVIEW CASES CAN BE CHANGED
        # -------------------------------------------------

        if (
            original_decision == "REVIEW"
            and manual_decision
        ):

            updated_candidate[
                "original_decision"
            ] = "REVIEW"

            updated_candidate[
                "decision"
            ] = manual_decision

            updated_candidate[
                "decision_source"
            ] = "HUMAN"

            if manual_decision == "MERGE":

                updated_candidate[
                    "reason"
                ] = (
                    "Human reviewer approved the merge "
                    "after reviewing the ambiguous evidence."
                )

            else:

                updated_candidate[
                    "reason"
                ] = (
                    "Human reviewer chose to keep the "
                    "ambiguous records separate."
                )

        else:

            updated_candidate[
                "decision_source"
            ] = candidate.get(
                "decision_source",
                "AUTOMATIC"
            )

        updated_candidates.append(
            make_json_safe(
                updated_candidate
            )
        )

    # -----------------------------------------------------
    # SAFE MERGE CHECK
    # -----------------------------------------------------

    validate_safe_merge_graph(
        updated_candidates
    )

    # -----------------------------------------------------
    # REBUILD ORIGINAL DATAFRAME
    # -----------------------------------------------------

    df = pd.DataFrame(
        request.records
    )

    if df.empty:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot apply decisions because "
                "the dataset is empty."
            )
        )

    # -----------------------------------------------------
    # REBUILD MASTER DATASET
    # -----------------------------------------------------

    master_df = build_master_dataset(
        df,
        updated_candidates
    )

    # -----------------------------------------------------
    # UPDATED COUNTS
    # -----------------------------------------------------

    merge_count = sum(
        1
        for candidate in updated_candidates
        if candidate.get("decision") == "MERGE"
    )

    review_count = sum(
        1
        for candidate in updated_candidates
        if candidate.get("decision") == "REVIEW"
    )

    separate_count = sum(
        1
        for candidate in updated_candidates
        if candidate.get("decision") == "KEEP_SEPARATE"
    )

    # -----------------------------------------------------
    # UPDATED QUALITY REPORT
    # -----------------------------------------------------

    data_quality_report = (
        create_data_quality_report(
            df,
            updated_candidates,
            master_df
        )
    )

    response = {

        "success":
            True,

        "message":
            "Human review decisions applied successfully.",

        "summary": {

            "candidate_pairs":
                len(updated_candidates),

            "merge":
                merge_count,

            "review":
                review_count,

            "keep_separate":
                separate_count
        },

        "data_quality_report":
            data_quality_report,

        "master_record_count":
            len(master_df),

        "master_data":
            make_json_safe(
                master_df.to_dict(
                    orient="records"
                )
            ),

        "candidates":
            make_json_safe(
                updated_candidates
            )
    }

    return make_json_safe(
        response
    )


# =========================================================
# EXPORT CLEAN CSV
# =========================================================

@app.post("/export/csv")
def export_clean_csv(
    request: ExportRequest
):

    if not request.master_data:

        raise HTTPException(
            status_code=400,
            detail=(
                "There is no master data to export."
            )
        )

    df = pd.DataFrame(
        request.master_data
    )

    df = df.fillna("")

    output = io.StringIO()

    df.to_csv(
        output,
        index=False
    )

    csv_bytes = io.BytesIO(
        output
        .getvalue()
        .encode("utf-8-sig")
    )

    csv_bytes.seek(0)

    return StreamingResponse(
        csv_bytes,

        media_type=(
            "text/csv; charset=utf-8"
        ),

        headers={
            "Content-Disposition":
                'attachment; filename="clean_master_dataset.csv"'
        }
    )


# =========================================================
# EXPORT CLEAN XLSX
# =========================================================

@app.post("/export/xlsx")
def export_clean_xlsx(
    request: ExportRequest
):

    if not request.master_data:

        raise HTTPException(
            status_code=400,
            detail=(
                "There is no master data to export."
            )
        )

    df = pd.DataFrame(
        request.master_data
    )

    df = df.fillna("")

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Clean Master Data",
            index=False
        )

        worksheet = writer[
            "Clean Master Data"
        ]

        # Auto-size columns
        for column_cells in worksheet.columns:

            max_length = 0

            column_letter = (
                column_cells[0]
                .column_letter
            )

            for cell in column_cells:

                try:

                    cell_length = len(
                        str(
                            cell.value
                            if cell.value is not None
                            else ""
                        )
                    )

                    max_length = max(
                        max_length,
                        cell_length
                    )

                except Exception:
                    pass

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 2,
                45
            )

    output.seek(0)

    return StreamingResponse(
        output,

        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),

        headers={
            "Content-Disposition":
                'attachment; filename="clean_master_dataset.xlsx"'
        }
    )


# =========================================================
# EXPORT DECISION LOG
# =========================================================

@app.post("/export/decision-log")
def export_decision_log(
    request: ExportRequest
):

    if not request.candidates:

        raise HTTPException(
            status_code=400,
            detail=(
                "There are no candidate decisions "
                "to export."
            )
        )

    log_records = []

    for candidate in request.candidates:

        field_scores = (
            candidate.get(
                "field_scores",
                {}
            )
            or {}
        )

        conflict_flags = (
            candidate.get(
                "conflict_flags",
                {}
            )
            or {}
        )

        ai_review = (
            candidate.get(
                "ai_review"
            )
            or {}
        )

        log_records.append({

            "record_1_id":
                candidate.get(
                    "record_1_id",
                    ""
                ),

            "record_2_id":
                candidate.get(
                    "record_2_id",
                    ""
                ),

            "decision":
                candidate.get(
                    "decision",
                    ""
                ),

            "original_decision":
                candidate.get(
                    "original_decision",
                    candidate.get(
                        "decision",
                        ""
                    )
                ),

            "decision_source":
                candidate.get(
                    "decision_source",
                    "AUTOMATIC"
                ),

            "confidence":
                candidate.get(
                    "score",
                    ""
                ),

            "reason":
                candidate.get(
                    "reason",
                    ""
                ),

            "name_score":
                field_scores.get(
                    "name",
                    ""
                ),

            "email_score":
                field_scores.get(
                    "email",
                    ""
                ),

            "phone_score":
                field_scores.get(
                    "phone",
                    ""
                ),

            "address_score":
                field_scores.get(
                    "address",
                    ""
                ),

            "city_score":
                field_scores.get(
                    "city",
                    ""
                ),

            "email_conflict":
                conflict_flags.get(
                    "email_conflict",
                    False
                ),

            "phone_conflict":
                conflict_flags.get(
                    "phone_conflict",
                    False
                ),

            "address_conflict":
                conflict_flags.get(
                    "address_conflict",
                    False
                ),

            "city_conflict":
                conflict_flags.get(
                    "city_conflict",
                    False
                ),

            "ai_recommendation":
                ai_review.get(
                    "ai_decision",
                    ""
                ),

            "ai_reason":
                ai_review.get(
                    "ai_reason",
                    ""
                ),

            "human_review_required":
                ai_review.get(
                    "requires_human_review",
                    False
                )
        })

    log_df = pd.DataFrame(
        log_records
    )

    log_df = log_df.fillna("")

    output = io.StringIO()

    log_df.to_csv(
        output,
        index=False
    )

    log_bytes = io.BytesIO(
        output
        .getvalue()
        .encode("utf-8-sig")
    )

    log_bytes.seek(0)

    return StreamingResponse(
        log_bytes,

        media_type=(
            "text/csv; charset=utf-8"
        ),

        headers={
            "Content-Disposition":
                'attachment; filename="decision_log.csv"'
        }
    )