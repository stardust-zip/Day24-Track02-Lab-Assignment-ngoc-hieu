from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

# Path to raw patient data
RAW_DATA_PATH = (
    Path(__file__).parent.parent.parent / "data" / "raw" / "patients_raw.csv"
)


def _load_raw_data() -> pd.DataFrame:
    """Load raw patient data from CSV, caching in memory."""
    if not RAW_DATA_PATH.exists():
        # Generate if not present
        from src.data_generator import generate_patients

        generate_patients(100)
    return pd.read_csv(RAW_DATA_PATH)


# --- ENDPOINT 1 ---
@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    """
    Trả về raw patient data (chỉ admin được phép).
    Load từ data/raw/patients_raw.csv
    Trả về 10 records đầu tiên dưới dạng JSON.
    """
    df = _load_raw_data()
    records = df.head(10).to_dict(orient="records")
    return JSONResponse(
        content={
            "count": len(records),
            "data": records,
        }
    )


# --- ENDPOINT 2 ---
@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    """
    Trả về anonymized data (ml_engineer và admin được phép).
    Load raw data → anonymize → trả về JSON.
    """
    df = _load_raw_data()
    df_anon = anonymizer.anonymize_dataframe(df)
    records = df_anon.to_dict(orient="records")
    return JSONResponse(
        content={
            "count": len(records),
            "data": records,
        }
    )


# --- ENDPOINT 3 ---
@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    """
    Trả về aggregated metrics (data_analyst, ml_engineer, admin).
    Ví dụ: số bệnh nhân theo từng loại bệnh (không có PII).
    """
    df = _load_raw_data()

    # Disease distribution
    disease_counts = df["benh"].value_counts().to_dict()

    # Test result summary
    test_counts = df["ket_qua_xet_nghiem"].value_counts().to_dict()

    # Age statistics (approximate from DOB if present)
    age_stats = {}
    if "ngay_sinh" in df.columns:
        from datetime import datetime

        current_year = datetime.now().year
        years = df["ngay_sinh"].dropna().astype(str).str[:4].astype(int)
        ages = current_year - years
        age_stats = {
            "mean": float(ages.mean()),
            "min": int(ages.min()),
            "max": int(ages.max()),
        }

    return JSONResponse(
        content={
            "total_patients": len(df),
            "disease_distribution": disease_counts,
            "test_result_summary": test_counts,
            "age_statistics": age_stats,
        }
    )


# --- ENDPOINT 4 ---
@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Chỉ admin được xóa. Các role khác nhận 403.
    """
    df = _load_raw_data()

    if patient_id not in df["patient_id"].values:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    # In production this would delete from DB; here we just confirm authorization
    return JSONResponse(
        content={
            "message": f"Patient '{patient_id}' deleted successfully",
            "deleted_by": current_user["username"],
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
