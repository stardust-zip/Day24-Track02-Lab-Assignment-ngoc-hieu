import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("vi_VN")


def _generate_cccd() -> str:
    """Generate a fake 12-digit CCCD number."""
    return "".join(random.choices(string.digits, k=12))


def _generate_phone() -> str:
    """Generate a fake Vietnamese phone number (0xx xxxx xxx)."""
    prefixes = ["03", "05", "07", "08", "09"]
    prefix = random.choice(prefixes)
    rest = "".join(random.choices(string.digits, k=9))
    return f"{prefix}{rest}"


def _generate_email(name: str) -> str:
    """Generate a fake email from a name."""
    name_part = name.lower().replace(" ", ".")
    domains = ["gmail.com", "yahoo.com", "email.com", "outlook.com"]
    return f"{name_part}{random.randint(1, 99)}@{random.choice(domains)}"


def _generate_address() -> str:
    """Generate a fake Vietnamese address."""
    return fake.address().replace("\n", ", ")


def _generate_dob() -> str:
    """Generate a random date of birth (1950-2010)."""
    start = datetime(1950, 1, 1)
    end = datetime(2010, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    dob = start + timedelta(days=random_days)
    return dob.strftime("%Y-%m-%d")


DISEASES = [
    "Tiểu đường type 2",
    "Tăng huyết áp",
    "Bệnh tim mạch",
    "Viêm phổi",
    "Viêm khớp dạng thấp",
    "Gan nhiễm mỡ",
    "Suy thận mạn",
    "Bệnh phổi tắc nghẽn mãn tính",
    "Đau thắt ngực",
    "Rối loạn lipid máu",
    "Bệnh tuyến giáp",
    "Bệnh dạ dày",
    "Đái tháo đường",
    "Bệnh Alzheimer",
    "Bệnh Parkinson",
]

TEST_RESULTS = [
    "HbA1c: 7.2%",
    "HbA1c: 6.5%",
    "HbA1c: 8.1%",
    "Huyết áp: 140/90 mmHg",
    "Huyết áp: 120/80 mmHg",
    "Huyết áp: 160/100 mmHg",
    "Cholesterol: 220 mg/dL",
    "Cholesterol: 180 mg/dL",
    "HDL: 55 mg/dL",
    "LDL: 130 mg/dL",
    "LDL: 160 mg/dL",
    "Glucose: 95 mg/dL",
    "Glucose: 140 mg/dL",
    "eGFR: 75 mL/min/1.73m2",
    "eGFR: 45 mL/min/1.73m2",
    "CT scan: Không bất thường",
    "X-quang ngực: Bình thường",
    "MRI não: Không phát hiện bệnh lý",
]


def generate_patients(n: int = 100) -> pd.DataFrame:
    """
    Generate a DataFrame with n patient records containing realistic
    Vietnamese PII data.

    Columns: patient_id, ho_ten, cccd, so_dien_thoai, email,
             dia_chi, ngay_sinh, benh, ket_qua_xet_nghiem
    """
    records = []
    for i in range(1, n + 1):
        name = fake.name()
        cccd = _generate_cccd()
        phone = _generate_phone()
        email = _generate_email(name)
        address = _generate_address()
        dob = _generate_dob()
        disease = random.choice(DISEASES)
        test_result = random.choice(TEST_RESULTS)

        records.append(
            {
                "patient_id": f"P{i:05d}",
                "ho_ten": name,
                "cccd": cccd,
                "so_dien_thoai": phone,
                "email": email,
                "dia_chi": address,
                "ngay_sinh": dob,
                "benh": disease,
                "ket_qua_xet_nghiem": test_result,
            }
        )

    df = pd.DataFrame(records)

    # Also save to CSV
    output_dir = Path(__file__).parent.parent / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "patients_raw.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")

    return df


if __name__ == "__main__":
    df = generate_patients(100)
    print(f"Generated {len(df)} records -> data/raw/patients_raw.csv")
    print(df.head())
    print(df.shape)
    print(df.dtypes)
