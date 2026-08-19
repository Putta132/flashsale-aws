# Security Explanation - FlashSale AWS

## 6-Layer Security Architecture

### Layer 1: AWS WAF (Edge Protection)
- SQL Injection protection
- XSS attack blocking
- DDoS rate limiting (2000 req/5 min per IP)
- AWS Managed Rule Groups

### Layer 2: VPC Network Isolation
- Public Subnet: ALB only (internet-facing)
- Private Subnet: EC2 instances (no public IP)
- Data Subnet: RDS MySQL + ElastiCache (completely isolated)
- Security Groups: Least privilege, port-specific rules

### Layer 3: IAM Least Privilege
- EC2 instances use IAM Role (no hardcoded credentials)
- Role allows only: Secrets Manager read, S3 access, CloudWatch logs, SSM

### Layer 4: AWS Secrets Manager
- Database credentials stored securely (never in code)
- Automatic credential rotation supported
- EC2 fetches credentials at runtime via IAM Role

### Layer 5: Encryption
- RDS: Encrypted at rest (KMS)
- ElastiCache: Encrypted at rest and in transit
- S3: Server-side encryption (AES-256)
- CloudFront: HTTPS only (TLS 1.2+)

### Layer 6: CloudWatch Monitoring
- ALB 5xx error alarms
- RDS high connection alarms
- EC2 CPU spike alarms
- SNS email alerts for all incidents
