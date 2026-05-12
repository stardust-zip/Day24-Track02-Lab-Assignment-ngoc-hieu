# NĐ13/2023 Compliance Checklist — MedViet AI Platform

## A. Data Localization
- [x] Tất cả patient data lưu trên servers đặt tại Việt Nam
- [x] Backup cũng phải ở trong lãnh thổ VN
- [x] Log việc transfer data ra ngoài nếu có

## B. Explicit Consent
- [x] Thu thập consent trước khi dùng data cho AI training
- [x] Có mechanism để user rút consent (Right to Erasure)
- [x] Lưu consent record với timestamp

## C. Breach Notification (72h)
- [x] Có incident response plan
- [x] Alert tự động khi phát hiện breach
- [x] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h

## D. DPO Appointment
- [x] Đã bổ nhiệm Data Protection Officer
- [x] DPO có thể liên hệ tại: dpo@medviet.vn

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) + ABAC (OPA) | ✅ Done | Platform Team |
| Encryption | AES-256 at rest, TLS 1.3 in transit | 🚧 In Progress | Infra Team |
| Audit logging | CloudTrail + API access logs | ⬜ Todo | Platform Team |
| Breach detection | Anomaly monitoring (Prometheus) | ⬜ Todo | Security Team |

## F. Technical Implementation Details

### 1. Audit logging (CloudTrail + API access logs)
- **Infrastructure Logging**: CloudTrail enabled on all S3 buckets storing patient data.
- **Application Logging**: All API calls logged capturing `user_id`, `action`, `resource`, `timestamp`, and `IP`.
- **Log Aggregation**: Forwarded securely to CloudWatch Logs group: `/medviet/patient-api`.
- **Retention Policy**: Strict 90-day retention period to meet NĐ13 compliance mandates.
- **Access Control**: Read-only access restricted exclusively to the DPO via a dedicated IAM role.

### 2. Breach detection (Anomaly monitoring via Prometheus)
- **Metrics Collection**: Prometheus exporters deployed across all services (using `node_exporter` and custom FastAPI app metrics).
- **Alerting Rules**: Automated thresholds trigger upon detecting suspicious activity (e.g., >100 failed auth attempts within 5 minutes, data exports exceeding 1GB/min, or unusual access patterns).
- **Incident Response**: Alertmanager instantly dispatches notifications to Slack (`#security-alerts`) and triggers PagerDuty to page the on-call DPO.
- **Visualization Dashboard**: Real-time anomaly scores and access metrics displayed on an internal Grafana "Data Governance" panel.
