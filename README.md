# Email Phishing Detector & AWS Monitoring Infrastructure

## Overview
This project implements an Email Phishing Detector web application deployed on AWS using Terraform, designed with high availability, layered security, and CloudWatch observability.

---

## Part 1: Email Phishing Detector
- **Input:** Accepts `.txt` email files containing `From:`, `Subject:`, optional `Attachments:`, and the email body.
- **Weighted Risk Scoring (0–100):**
  - **Spoofed Sender (+40):** Checks domain extensions, excessive hyphens, digits in domain, character substitutions (`0→o`, `1→l`, etc.), and brand similarity using `difflib`.
  - **Dangerous Attachments (+30):** Flags risky extensions (`.exe`, `.bat`, `.js`, `.zip`, etc.) and double extensions.
  - **Suspicious Links (+20):** Detects raw IP URLs, unencrypted `http://` links, risky TLDs, and URL shorteners.
  - **Suspicious Wording (+10):** Scans subject and body for common urgency/phishing keywords.
- **Web UI & History:** Flask frontend (`templates/index.html`) displaying an overall risk circle and per-indicator circles color-coded by severity (Green/Orange/Red), plus a scan history table persisted in Amazon RDS.

---

## Part 2: AWS Infrastructure (Terraform)
All infrastructure is provisioned in `eu-north-1` via `terraform/`:
- `provider.tf` — AWS provider configuration.
- `network.tf` — VPC (`10.0.0.0/16`), Internet Gateway, 2 public subnets across 2 Availability Zones (`eu-north-1a`, `eu-north-1b`), and layered Security Groups.
- `rds.tf` — Amazon RDS PostgreSQL (`db.t3.micro`, non-publicly accessible).
- `compute.tf` — Private S3 bucket for app code, IAM Role (`CloudWatchAgentServerPolicy`, `AmazonS3ReadOnlyAccess`), 2 EC2 instances (`t3.micro`) running Flask + CloudWatch Agent, Application Load Balancer (ALB), Target Group with `/health` check, and CloudWatch Log Group (`/upwind/phishing-app`).

### Architecture Decisions
- **Availability:** 2 EC2 instances distributed across 2 Availability Zones behind an ALB with `/health` checks.
- **Security:** Layered Security Groups — ALB accepts port `80` from the internet; EC2 accepts port `5000` only from the ALB; RDS accepts port `5432` only from EC2 and is not publicly accessible. Database credentials are stored in a gitignored `terraform.tfvars`.
- **Permissions:** EC2 instances use an IAM Instance Profile with only S3 read-only and CloudWatch Agent permissions (no hardcoded AWS credentials).
- **Reliability:** Persistent scan history stored in Amazon RDS rather than local instance memory.

---

## Monitoring & Observability
1. **EC2 Health:** Verified via `EC2 -> Target Groups -> upwind-tg -> Targets` (`Healthy`) and `EC2 -> Instances -> Status check`.
2. **CPU & System Resources:** Monitored via `EC2 -> Instances -> Monitoring` (`CPUUtilization`).
3. **ALB Request Count:** Monitored via `EC2 -> Load Balancers -> upwind-alb -> Monitoring` (`RequestCount`).
4. **Success vs. Failure Rates:** Tracked via `HTTPCode_Target_2XX_Count`, `HTTPCode_ELB_4XX_Count`, and `HTTPCode_Target_5XX_Count`.
5. **Application Logs:** Streamed from both EC2 instances via CloudWatch Agent to `CloudWatch -> Logs -> /upwind/phishing-app`.

---

## Deployment & Cleanup (Live Demo)
1. Create `terraform/terraform.tfvars`:
   ```hcl
   db_password = "YourSecurePassword"