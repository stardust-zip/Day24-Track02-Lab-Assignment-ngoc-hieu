# Kế hoạch hoàn thành Lab Data Governance & Security — MedViet AI Platform

> **Mục tiêu:** Đạt ≥70đ (tối đa 100đ). Mỗi phần có check step rõ ràng.

---

## Tổng quan điểm & thứ tự ưu tiên

| Hạng mục | Điểm | Ưu tiên |
|----------|------|---------|
| PII Detection | 25đ | ⭐⭐⭐ |
| Anonymization | 20đ | ⭐⭐⭐ |
| RBAC API | 20đ | ⭐⭐⭐ |
| Encryption | 15đ | ⭐⭐ |
| Security Audit | 10đ | ⭐⭐ |
| Compliance Checklist | 10đ | ⭐ |

---

## Phần 1 — Chuẩn Bị Dữ Liệu (15 phút)

**Mục tiêu:** Tạo dataset giả lập đủ lớn, đa dạng PII.

**Check:**
- [x] `generate_patients()` chạy không lỗi
- [x] Output có ít nhất 50 records
- [x] Có đủ các loại PII: CCCD (9-12 số), phone (+84), email, tên, địa chỉ
- [x] Data lưu vào `data/raw/` hoặc trả về DataFrame

**Verification:**
```bash
python -c "
from src.data_generator import generate_patients
df = generate_patients(100)
print(df.shape)
print(df.dtypes)
print(df.head())
"
```

---

## Phần 2 — PII Detection & Anonymization (45 phút)

### 2.1 — Setup
**Check:**
- [ ] Cài đặt presidium-anonymizer, pandas-profiling, pytest
- [ ] Import không lỗi

**Verification:**
```bash
pip install microsoft-presidio-anonymizer presidio-analyzer presidio-anonymizer pandas pytest
python -c "from presidio_analyzer import PresidioAnalyzer; print('OK')"
```

---

### 2.2 — Custom Recognizers cho Tiếng Việt
**Mục tiêu:** Detect được CCCD VN và phone number Việt Nam.

**Check:**
- [ ] `build_vietnamese_analyzer()` trả về analyzer với custom pattern cho CCCD
- [ ] `detect_pii(text)` trả về list entities
- [ ] CCCD format: `\d{9}|\d{12}` được recognize
- [ ] Phone: `0\d{9,10}` hoặc `\+84` format

**Verification:**
```bash
python -c "
from src.pii_detector import build_vietnamese_analyzer, detect_pii
analyzer = build_vietnamese_analyzer()
results = detect_pii(analyzer, 'CCCD: 012345678901, SĐT: 0912345678')
print(results)
# Expected: 2 entities detected
"
```

---

### 2.3 — Anonymization Pipeline
**Mục tiêu:** MedVietAnonymizer hoạt động đúng cho text và DataFrame.

**Check:**
- [ ] `anonymize_text(text)` — thay CCCD bằng `<CCCD>`, phone bằng `<PHONE>`, email bằng `<EMAIL>`
- [ ] `anonymize_dataframe(df)` — áp dụng lên tất cả text columns, giữ nguyên non-text columns
- [ ] `calculate_detection_rate()` — tính đúng % PII được detect

**Verification:**
```bash
python -c "
from src.anonymizer import MedVietAnonymizer
az = MedVietAnonymizer()
text = 'Bệnh nhân A, CCCD: 012345678901, liên hệ: a@example.com'
result = az.anonymize_text(text)
print(result)
assert '<CCCD>' in result
assert '<EMAIL>' in result
print('OK')
"
```

---

### 2.4 — Tests
**Mục tiêu:** Tất cả tests pass → đảm bảo 25đ PII + 20đ Anonymization.

**Check:**
- [ ] `TestPIIDetection.test_cccd_detected` — PASS
- [ ] `TestPIIDetection.test_phone_detected` — PASS
- [ ] `TestPIIDetection.test_email_detected` — PASS
- [ ] `TestPIIDetection.test_detection_rate_above_95_percent` — PASS
- [ ] `TestAnonymization.test_pii_not_in_output` — PASS
- [ ] `TestAnonymization.test_non_pii_columns_unchanged` — PASS

**Verification:**
```bash
pytest tests/test_anonymizer.py -v
```

---

## Phần 3 — RBAC với Casbin & FastAPI (45 phút)

### 3.1 — Policy Definition
**Check:**
- [ ] File `policies/rbac_model.conf` tồn tại với sections: `[request_definition]`, `[policy_definition]`, `[role_definition]`, `[policy_effect]`, `[matchers]`
- [ ] 3 roles: `admin`, `data_analyst`, `intern` được định nghĩa
- [ ] Policies gán quyền cụ thể cho từng role

### 3.2 — RBAC Module
**Check:**
- [ ] `get_current_user(request)` — extract user từ header/token
- [ ] `require_permission(resource, action)` decorator hoạt động
- [ ] Decorator trả về 403 Forbidden khi không có quyền

**Verification:**
```bash
python -c "
from src.rbac import Enforcer, get_current_user, require_permission
e = Enforcer('policies/rbac_model.conf', 'policies/rbac_policy.csv')
# Test admin can access
print(e.enforce('admin', 'patient_data', 'read'))
# Test intern blocked
print(e.enforce('intern', 'patient_data', 'delete'))
"
```

---

### 3.3 — FastAPI Endpoints
**Mục tiêu:** 4 endpoints RBAC hoạt động đúng.

**Check:**
- [ ] `GET /patients/raw` — chỉ admin
- [ ] `GET /patients/anonymized` — admin + analyst
- [ ] `GET /metrics` — analyst
- [ ] `DELETE /patients/{id}` — chỉ admin

**Verification:**
```bash
# Start server
uvicorn src.api:app --host 0.0.0.0 --port 8000 &
sleep 2

# Test admin access
curl -H "X-User: admin" http://localhost:8000/patients/raw
# Expected: 200

# Test intern blocked
curl -H "X-User: intern" http://localhost:8000/patients/raw
# Expected: 403

pytest tests/test_api.py -v
```

---

## Phần 4 — Encryption (30 phút)

**Mục tiêu:** Envelope encryption đúng, không lưu plaintext key.

**Check:**
- [ ] `SimpleVault.__init__()` — tạo/học KEK từ environment variable hoặc file
- [ ] `generate_dek()` — tạo DEK ngẫu nhiên
- [ ] `encrypt_data(plaintext)` — mã hóa với DEK, rồi bọc DEK bằng KEK
- [ ] `decrypt_data(ciphertext)` — giải mã ngược đúng
- [ ] `encrypt_column(df, col_name)` — mã hóa toàn bộ column
- [ ] Round-trip: encrypt → decrypt phải trả về dữ liệu gốc
- [ ] Không lưu key dạng plaintext vào disk

**Verification:**
```bash
python -c "
from src.vault import SimpleVault
vault = SimpleVault()
original = 'Nguyen Van A'
enc = vault.encrypt_data(original)
dec = vault.decrypt_data(enc)
assert dec == original, 'Round-trip failed!'
print('Encryption round-trip: OK')
"

# Check no plaintext key
ls -la .vault_key 2>/dev/null && echo "WARN: key file exists" || echo "No plaintext key on disk: OK"
```

---

## Phần 5 — Data Quality Validation (20 phút)

**Mục tiêu:** Great Expectations validate data sau anonymization.

**Check:**
- [ ] `build_patient_expectation_suite()` — định nghĩa expectations cho patient data
- [ ] `validate_anonymized_data(df)` — chạy validation, trả về results
- [ ] Expectations kiểm tra: no nulls ở cột critical, schema đúng

**Verification:**
```bash
pip install great-expectations
python -c "
from src.quality_validator import build_patient_expectation_suite, validate_anonymized_data
import pandas as pd
suite = build_patient_expectation_suite()
df = pd.DataFrame({'name': ['Nguyen Van A', 'Tran Thi B'], 'age': [25, 30]})
results = validate_anonymized_data(df, suite)
print(results)
"
```

---

## Phần 6 — Security Scanning (20 phút)

### 6.1 — Git-Secrets Hook
**Check:**
- [ ] Cài git-secrets
- [ ] Hook đăng ký: `git secrets --install`
- [ ] Thêm patterns: AWS keys, generic secrets
- [ ] Test: commit với fake credential → bị reject

**Verification:**
```bash
git secrets --install
git secrets --add 'AKIA[0-9A-Z]{16}'
git secrets --add 'sk-[0-9a-zA-Z]{32}'

# Test hook blocks secret
echo "AWS_SECRET_KEY=sk_fake_key_12345678901234567890" > /tmp/test_secret.txt
git add /tmp/test_secret.txt
git commit -m "test" 2>&1 | grep -i "secret\|prohibited" && echo "Hook blocks secrets: OK"
```

---

### 6.2 — TruffleHog
**Check:**
- [ ] Cài trufflehog
- [ ] Scan repo → report không có verified secrets (chỉ có fake/placeholder)

**Verification:**
```bash
trufflehog git file://. --only-verified | tee reports/trufflehog_report.txt
# Expected: no secrets found (hoặc chỉ test credentials)
```

---

### 6.3 — Bandit SAST
**Check:**
- [ ] Scan `src/` với Bandit
- [ ] Report lưu vào `reports/bandit_report.json`
- [ ] Không có HIGH severity issues

**Verification:**
```bash
bandit -r src/ -f json -o reports/bandit_report.json
bandit -r src/ -f screen
# Check for HIGH issues
```

---

## Phần 7 — OPA Policy (15 phút)

**Mục tiêu:** Hoàn thiện 2 TODO rules trong `policies/opa_policy.rego`.

### 7.1 — Completar rule cho data_analyst
**Check:**
- [ ] Rule `allow` cho data_analyst chỉ với `resource in {"aggregated_metrics", "reports"}` và `action == "read"`
- [ ] data_analyst KHÔNG được write

**Expected rule:**
```rego
allow if {
    input.user.role == "data_analyst"
    input.resource in {"aggregated_metrics", "reports"}
    input.action == "read"
}
```

### 7.2 — Completar rule cho intern
**Check:**
- [ ] Rule `allow` cho intern chỉ với `resource == "sandbox"`

**Expected rule:**
```rego
allow if {
    input.user.role == "intern"
    input.resource == "sandbox"
    input.action in {"read", "write"}
}
```

### 7.3 — Verify
**Check:**
- [ ] ml_engineer không delete production_data → `deny` = true, `allow` = false
- [ ] data_analyst đọc aggregated_metrics → `allow` = true
- [ ] intern access sandbox → `allow` = true
- [ ] intern access production_data → `allow` = false

**Verification:**
```bash
brew install opa  # hoặc: curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64

# Test ml_engineer delete blocked
echo '{
  "user": {"role": "ml_engineer"},
  "resource": "production_data",
  "action": "delete"
}' | opa eval -d policies/opa_policy.rego -I "data.medviet.data_access.allow"
# Expected: false

# Test intern sandbox allowed
echo '{
  "user": {"role": "intern"},
  "resource": "sandbox",
  "action": "read"
}' | opa eval -d policies/opa_policy.rego -I "data.medviet.data_access.allow"
# Expected: true
```

---

## Phần 8 — Compliance Checklist (15 phút)

**Mục tiêu:** Điền đầy đủ phần TODO/F và mapping.

### 8.1 — Hoàn thành Section F
**Check:** Mô tả technical solution cho 2 row còn Todo:

**Audit logging:**
```markdown
| Audit logging | CloudTrail + API access logs | ⬜ Todo | Platform Team |

# Technical Solution:
# - CloudTrail enabled on all S3 buckets storing patient data
# - All API calls logged with: user_id, action, resource, timestamp, IP
# - Logs aggregated to CloudWatch Logs group: /medviet/patient-api
# - Retention: 90 days (NĐ13 requirement)
# - Access: DPO can query via ReadOnlyAccess role
```

**Breach detection:**
```markdown
| Breach detection | Anomaly monitoring (Prometheus) | ⬜ Todo | Security Team |

# Technical Solution:
# - Prometheus exporters on all services (node_exporter, custom app metrics)
# - Alerting rules: >100 failed auth/5min, data export >1GB/min, unusual access patterns
# - Alertmanager sends to: Slack #security-alerts + PagerDuty (DPO on-call)
# - Grafana dashboard: "Data Governance" panel showing anomaly scores
```

### 8.2 — Hoàn thành Section D
**Check:** Điền DPO contact

```markdown
| DPO Appointment | Đã bổ nhiệm Data Protection Officer | ✅ Done | Legal Team |
| DPO có thể liên hệ tại: dpo@medviet.vn | ✅ Done | Legal Team |
```

---

## Final Verification Checklist

Chạy tất cả check cuối cùng trước khi nộp:

```bash
# 1. All tests pass
pytest tests/ -v --tb=short

# 2. Encryption round-trip
python -c "
from src.vault import SimpleVault
vault = SimpleVault()
data = 'Sensitive Patient Data'
enc = vault.encrypt_data(data)
assert vault.decrypt_data(enc) == data, 'FAIL'
print('Encryption: PASS')
"

# 3. OPA policies
echo '{"user":{"role":"ml_engineer"},"resource":"production_data","action":"delete"}' \
  | opa eval -d policies/opa_policy.rego -I "data.medviet.data_access.allow"
# Must return: false

# 4. Bandit scan
bandit -r src/ -f screen | grep -E "HIGH| Severity"

# 5. TruffleHog (no real secrets)
trufflehog git file://. --only-verified

# 6. RBAC tests
pytest tests/test_api.py -v
```

---

## Thứ tự làm bài đề xuất (theo thời gian)

1. **Phần 1** (15p) → Setup data → Quick check
2. **Phần 2** (45p) → **Ưu tiên cao nhất (45đ)** → Viết code + tests → Chạy pytest
3. **Phần 3** (45p) → **Ưu tiên cao (20đ)** → Viết RBAC + API → Test từng endpoint
4. **Phần 4** (30p) → **Ưu tiên trung bình (15đ)** → Vault → Round-trip test
5. **Phần 5** (20p) → Great Expectations → Quick smoke test
6. **Phần 6** (20p) → Security scans → Lưu reports
7. **Phần 7** (15p) → OPA → Test 3 cases
8. **Phần 8** (15p) → Compliance checklist → Điền TODO

---

## Chiến lược đạt điểm tối đa

| Mục tiêu | Action |
|-----------|--------|
| **25đ PII Detection** | Đảm bảo CCCD/phone/email regex hoạt động; detection rate ≥95% |
| **20đ Anonymization** | Test `test_pii_not_in_output` và `test_non_pii_columns_unchanged` phải PASS |
| **20đ RBAC** | 3 roles đúng; 403 trả về đúng; pytest pass |
| **15đ Encryption** | Round-trip encrypt/decrypt phải đúng; không lưu plaintext key |
| **10đ Security** | git-secrets hook hoạt động; bandit report có HIGH severity = 0 |
| **10đ Compliance** | Điền đầy đủ F, audit logging, breach detection bằng technical language |

> **Lưu ý:** Nếu hết thời gian, ưu tiên hoàn thành Phần 2 và 3 (tổng 45đ) trước.
