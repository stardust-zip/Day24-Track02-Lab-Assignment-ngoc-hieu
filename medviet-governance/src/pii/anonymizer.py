import hashlib

import pandas as pd
from faker import Faker
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


class MedVietAnonymizer:
    """MedViet PII anonymization pipeline."""

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """
        Anonymize text with the chosen strategy.

        Strategies:
        - "replace" : replace with fake data (using Faker)
        - "mask"    : mask characters (Nguyen Van A → N****** V** A)
        - "hash"    : SHA-256 one-way hash
        - "generalize": generalize dates/ages
        """
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "VN_PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "VN_EMAIL": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig(
                    "replace", {"new_value": fake.bothify("##########")}
                ),
                "VN_PHONE": OperatorConfig(
                    "replace", {"new_value": fake.phone_number()}
                ),
            }
        elif strategy == "mask":
            operators = {
                "PERSON": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 10,
                        "from_end": True,
                    },
                ),
                "VN_PERSON": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 10,
                        "from_end": True,
                    },
                ),
                "VN_EMAIL": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 6,
                        "from_end": True,
                    },
                ),
                "VN_CCCD": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 8,
                        "from_end": True,
                    },
                ),
                "VN_PHONE": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 7,
                        "from_end": True,
                    },
                ),
            }
        elif strategy == "hash":

            def _hash(entity_text: str, **_kwargs) -> str:
                return hashlib.sha256(entity_text.encode()).hexdigest()[:16]

            operators = {
                "PERSON": OperatorConfig("custom", {"lambda": _hash}),
                "VN_PERSON": OperatorConfig("custom", {"lambda": _hash}),
                "VN_EMAIL": OperatorConfig("custom", {"lambda": _hash}),
                "VN_CCCD": OperatorConfig("custom", {"lambda": _hash}),
                "VN_PHONE": OperatorConfig("custom", {"lambda": _hash}),
            }
        else:
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "VN_PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "VN_EMAIL": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig(
                    "replace", {"new_value": fake.bothify("##########")}
                ),
                "VN_PHONE": OperatorConfig(
                    "replace", {"new_value": fake.phone_number()}
                ),
            }

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Anonymize entire DataFrame.

        - Text columns (ho_ten, dia_chi, email): use anonymize_text()
        - CCCD and so_dien_thoai: replace directly with fake data
        - benh, ket_qua_xet_nghiem: keep unchanged (needed for model training)
        - patient_id: keep unchanged (pseudonym is safe enough)
        """
        df_anon = df.copy()

        # Text columns: apply anonymize_text row by row
        text_columns = ["ho_ten", "dia_chi", "email"]
        for col in text_columns:
            if col in df_anon.columns:
                df_anon[col] = (
                    df_anon[col]
                    .astype(str)
                    .apply(lambda x: self.anonymize_text(x, strategy="replace"))
                )

        # Direct fake replacement for structured columns
        if "cccd" in df_anon.columns:
            df_anon["cccd"] = [fake.bothify("##########") for _ in range(len(df_anon))]
        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = [
                fake.phone_number() for _ in range(len(df_anon))
            ]

        return df_anon

    def calculate_detection_rate(
        self, original_df: pd.DataFrame, pii_columns: list
    ) -> float:
        """
        Calculate the percentage of PII cells successfully detected.
        Target: > 95%
        """
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col].astype(str):
                total += 1
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        rate = detected / total if total > 0 else 0.0
        return rate
