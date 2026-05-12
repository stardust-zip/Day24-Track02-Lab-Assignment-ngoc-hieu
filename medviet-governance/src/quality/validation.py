# src/quality/validation.py
"""Data quality validation for MedViet anonymized patient data."""

import re
from typing import List, Optional

import pandas as pd


def build_patient_expectation_suite() -> dict:
    """
    Tạo expectation suite cho anonymized patient data.
    Returns a dict of expectation definitions that can be used for validation.
    """
    expectations = {
        "patient_id_not_null": {
            "column": "patient_id",
            "check": "not_null",
            "description": "patient_id không được null",
        },
        "cccd_length_12": {
            "column": "cccd",
            "check": "length_equals",
            "value": 12,
            "description": "CCCD phải có đúng 12 ký tự",
        },
        "ket_qua_between": {
            "column": "ket_qua_xet_nghiem",
            "check": "between",
            "min_value": 0,
            "max_value": 50,
            "description": "ket_qua_xet_nghiem phải trong khoảng [0, 50]",
        },
        "benh_in_set": {
            "column": "benh",
            "check": "in_set",
            "value_set": ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"],
            "description": "benh phải thuộc danh sách hợp lệ",
        },
        "email_regex": {
            "column": "email",
            "check": "regex",
            "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "description": "email phải match regex pattern",
        },
        "patient_id_unique": {
            "column": "patient_id",
            "check": "unique",
            "description": "Không được có duplicate patient_id",
        },
    }
    return expectations


def _run_expectation(df: pd.DataFrame, exp_def: dict) -> dict:
    """Run a single expectation check against a DataFrame."""
    col = exp_def["column"]
    check = exp_def["check"]

    result = {
        "check_name": list(exp_def.keys())[0],
        "column": col,
        "description": exp_def["description"],
        "success": True,
        "message": "PASS",
    }

    if col not in df.columns:
        result["success"] = False
        result["message"] = f"Column '{col}' not found"
        return result

    series = df[col]

    if check == "not_null":
        null_count = int(series.isnull().sum())
        if null_count > 0:
            result["success"] = False
            result["message"] = f"{null_count} null values found"

    elif check == "length_equals":
        expected_len = exp_def["value"]
        non_match = series.astype(str).str.len() != expected_len
        count = int(non_match.sum())
        if count > 0:
            result["success"] = False
            result["message"] = f"{count} values with length != {expected_len}"

    elif check == "between":
        min_val = exp_def["min_value"]
        max_val = exp_def["max_value"]
        out_of_range = (series < min_val) | (series > max_val)
        count = int(out_of_range.sum())
        if count > 0:
            result["success"] = False
            result["message"] = f"{count} values outside [{min_val}, {max_val}]"

    elif check == "in_set":
        value_set = exp_def["value_set"]
        not_in_set = ~series.isin(value_set)
        count = int(not_in_set.sum())
        if count > 0:
            result["success"] = False
            result["message"] = f"{count} values not in allowed set"

    elif check == "regex":
        pattern = exp_def["regex"]
        not_match = ~series.astype(str).str.match(pattern)
        count = int(not_match.sum())
        if count > 0:
            result["success"] = False
            result["message"] = f"{count} values don't match regex"

    elif check == "unique":
        total = len(series)
        unique = series.nunique()
        if unique != total:
            result["success"] = False
            result["message"] = f"{total - unique} duplicate values found"

    return result


def validate_anonymized_data(df: pd.DataFrame, suite: dict = None) -> dict:
    """
    Validate anonymized data.
    Trả về dict: {"success": bool, "failed_checks": list, "stats": dict}
    """
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {"total_rows": len(df), "columns": list(df.columns)},
    }

    # Check 1: Không còn CCCD gốc dạng số thuần túy
    if "cccd" in df.columns:
        original_cccd_pattern = r"^\d{9}$|^\d{12}$"
        mask_column = df["cccd"].astype(str).str.match(original_cccd_pattern)
        if mask_column.any():
            results["success"] = False
            results["failed_checks"].append(
                {
                    "check": "cccd_not_original",
                    "message": "CCCD vẫn còn dạng số thuần túy (chưa được anonymized)",
                    "count": int(mask_column.sum()),
                }
            )

    # Check 2: Không có null values trong các cột quan trọng
    critical_columns = ["patient_id", "name", "cccd"]
    for col in critical_columns:
        if col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                results["success"] = False
                results["failed_checks"].append(
                    {
                        "check": "null_values",
                        "column": col,
                        "message": f"Cột '{col}' có {null_count} giá trị null",
                        "count": null_count,
                    }
                )

    # Check 3: Số rows phải > 0
    if len(df) == 0:
        results["success"] = False
        results["failed_checks"].append(
            {"check": "empty_dataframe", "message": "DataFrame rỗng"}
        )

    # Check 4: Schema đúng
    required_cols = ["patient_id", "cccd", "ket_qua_xet_nghiem", "benh", "email"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        results["success"] = False
        results["failed_checks"].append(
            {
                "check": "missing_columns",
                "message": f"Thiếu các cột: {missing}",
                "missing": missing,
            }
        )

    # Nếu có suite, chạy Great Expectations-style validation
    if suite is not None:
        ge_results = []
        for exp_name, exp_def in suite.items():
            ge_result = _run_expectation(df, exp_def)
            ge_results.append(ge_result)
            if not ge_result["success"]:
                results["success"] = False

        results["stats"]["great_expectations"] = {
            "total": len(ge_results),
            "passed": sum(1 for r in ge_results if r["success"]),
            "failed": sum(1 for r in ge_results if not r["success"]),
            "details": ge_results,
        }

        for r in ge_results:
            if not r["success"]:
                results["failed_checks"].append(
                    {
                        "check": "great_expectations",
                        "expectation": r["description"],
                        "message": r["message"],
                    }
                )

    return results
