# ⚡ FlashSale AWS — E-Commerce Flash Sale Architecture
> **FortuneCloud AWS Challenge | Individual Submission**
> 🌐 Live Domain: https://samdevops.online | Region: ap-south-1 (Mumbai)

---

## Overview
A scalable, highly available, secure, and cost-optimized e-commerce cloud platform designed to handle unpredictable flash sale traffic spikes without crashes or downtime.

When a user visits **samdevops.online**, they see a live e-commerce website with 5 products, discount pricing, cart, and checkout — all powered by AWS services running in Mumbai region.

---

## Architecture
```
User -> Route 53 -> CloudFront -> AWS WAF -> ALB -> EC2 Auto Scaling (2-20)
                                                          |
                                              ElastiCache Redis (Cache)
                                              RDS MySQL Multi-AZ (Private Subnet DB)
                                              S3 (Assets) | Secrets Manager | CloudWatch | SNS
```

---

## AWS Services Used

| Service | Role |
|---|---|
| Route 53 | DNS for samdevops.online |
| CloudFront | CDN - Global content delivery |
| AWS WAF | DDoS, SQL injection, bot protection |
| ALB | Load balancing across EC2 instances |
| EC2 + Auto Scaling | Backend FastAPI app (scales 2 to 20) |
| ElastiCache Redis | Product cache + shopping cart storage |
| RDS MySQL Multi-AZ | Products and orders database (Private Subnet) |
| S3 | Static assets + lifecycle tiering |
| Secrets Manager | Secure DB credential storage |
| CloudWatch | Metrics, alarms, dashboard |
| SNS | Email alerts on incidents |
| VPC + Subnets | Network isolation - 3 tiers |

---

## Security Highlights
- Database in **private DATA subnets** - no internet access
- EC2 in **private subnets** - only ALB can reach it
- AWS WAF blocks DDoS, SQL injection, bots
- Secrets Manager stores DB credentials (never hardcoded)
- IAM least-privilege roles for EC2

---

## Scalability Highlights
- Auto Scaling: 2 to 20 EC2 instances based on CPU
- Redis distributed lock prevents overselling during checkout
- Multi-AZ RDS + ElastiCache for high availability

---

## Cost Optimization
- ~$71/month estimated
- Redis caching reduces DB reads by 95%
- Auto Scaling eliminates idle server costs
- S3 lifecycle moves old assets to cheaper storage tiers

---

## Deployment Steps

### Step 1: Create ACM Certificate (us-east-1 ONLY)
```
AWS Console -> Switch to us-east-1
ACM -> Request Certificate -> samdevops.online + *.samdevops.online
Copy Certificate ARN
Switch back to ap-south-1
```

### Step 2: Deploy CloudFormation (ap-south-1)
```
AWS Console -> CloudFormation -> Create Stack
Upload: infrastructure/cloudformation.yaml
Wait for CREATE_COMPLETE (~20 mins)
```

### Step 3: Update Domain Nameservers
```
CloudFormation Outputs -> Copy Route53 NS records
Hostinger DNS -> Replace nameservers with Route53 NS records
```

### Step 4: Start Backend on EC2
```bash
pip3 install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step 5: Test
```
https://samdevops.online        -> E-commerce website
https://samdevops.online/health -> Service health check
https://samdevops.online/products -> Products API
```

---

## Project Structure
```
flashsale-aws/
├── app/
│   ├── main.py               # FastAPI backend (products, cart, orders)
│   ├── index.html            # Frontend e-commerce UI
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variables template
├── infrastructure/
│   └── cloudformation.yaml   # Complete AWS infrastructure
├── docs/
│   ├── security-explanation.md
│   └── cost-optimization.md
├── architecture/
│   └── diagram.md
└── README.md
```
Author
Prateek Kulkarni
