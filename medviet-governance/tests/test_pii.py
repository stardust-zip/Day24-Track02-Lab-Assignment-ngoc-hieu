import pandas as pd
import pytest

from src.pii.anonymizer import MedVietAnonymizer


@pytest.fixture
def anonymizer():
    return MedVietAnonymizer()


@pytest.fixture
def sample_df():
    return pd.read_csv("data/raw/patients_raw.csv").head(50)


class TestPIIDetection:
    def test_cccd_detected(self, anonymizer):
        text = "Bệnh nhân Nguyen Van A, CCCD: 012345678901"
        results = anonymizer.analyzer.analyze(
            text=text, language="vi", entities=["VN_CCCD"]
        )
        assert len(results) >= 1, "CCCD should be detected"
        assert results[0].entity_type == "VN_CCCD"

    def test_phone_detected(self, anonymizer):
        text = "Liên hệ: 0912345678"
        results = anonymizer.analyzer.analyze(
            text=text, language="vi", entities=["VN_PHONE"]
        )
        assert len(results) >= 1, "Phone number should be detected"
        assert results[0].entity_type == "VN_PHONE"

    def test_email_detected(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        results = anonymizer.analyzer.analyze(
            text=text, language="vi", entities=["VN_EMAIL"]
        )
        assert len(results) >= 1, "Email should be detected"
        assert results[0].entity_type == "VN_EMAIL"

    def test_detection_rate_above_95_percent(self, anonymizer, sample_df):
        """Pipeline phải đạt >95% detection rate."""
        pii_columns = ["ho_ten", "cccd", "so_dien_thoai", "email"]
        rate = anonymizer.calculate_detection_rate(sample_df, pii_columns)
        print(f"\nDetection rate: {rate:.2%}")
        assert rate >= 0.95, f"Detection rate {rate:.2%} < 95%"


class TestAnonymization:
    def test_pii_not_in_output(self, anonymizer, sample_df):
        """Sau anonymization, không còn CCCD gốc trong output."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        for original_cccd in sample_df["cccd"]:
            cccd_str = str(original_cccd)
            for col in df_anon.columns:
                cell_values = df_anon[col].astype(str).tolist()
                assert cccd_str not in cell_values, (
                    f"Original CCCD {cccd_str} found in column {col}"
                )

    def test_non_pii_columns_unchanged(self, anonymizer, sample_df):
        """Cột benh và ket_qua_xet_nghiem phải giữ nguyên."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        pd.testing.assert_series_equal(
            sample_df["benh"].reset_index(drop=True),
            df_anon["benh"].reset_index(drop=True),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            sample_df["ket_qua_xet_nghiem"].reset_index(drop=True),
            df_anon["ket_qua_xet_nghiem"].reset_index(drop=True),
            check_names=False,
        )

    def test_anonymize_text_replaces_cccd(self, anonymizer):
        text = "Bệnh nhân A, CCCD: 012345678901"
        result = anonymizer.anonymize_text(text)
        assert "<CCCD>" in result or "012345678901" not in result

    def test_anonymize_text_replaces_email(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        result = anonymizer.anonymize_text(text)
        assert "nguyenvana@gmail.com" not in result

    def test_anonymize_text_replaces_phone(self, anonymizer):
        text = "Liên hệ: 0912345678"
        result = anonymizer.anonymize_text(text)
        assert "0912345678" not in result
