# Cost Optimization - FlashSale AWS

## Estimated Monthly Cost: ~USD 68/month

## Key Optimizations

### 1. EC2 Auto Scaling (Save 60-70%)
- Min 2 instances during low traffic
- Scales up to 20 during flash sale
- Pay only for what you use
- Target: CPU at 70% before scaling

### 2. ElastiCache Redis (Reduces RDS cost by 95%)
- Product data cached for 5 minutes
- Cart stored in Redis (not DB)
- Allows using cheap db.t3.micro for RDS
- 95% of reads served from cache

### 3. S3 Lifecycle Rules
- 0-90 days: S3 Standard
- 90-365 days: S3 Infrequent Access (40% cheaper)
- 365+ days: Glacier (80% cheaper)

### 4. CloudFront CDN
- Static files (HTML, images) served from edge
- Reduces EC2 load by 80%+
- Lower data transfer costs

### 5. RDS Right-Sizing
- db.t3.micro sufficient because Redis handles 95% of reads
- Multi-AZ for HA without expensive instance type

## Cost Breakdown
| Service | Monthly Cost |
|---|---|
| EC2 (2x t3.micro avg) | ~ |
| RDS MySQL Multi-AZ (db.t3.micro) | ~ |
| ElastiCache Redis (cache.t3.micro) | ~ |
| ALB | ~ |
| CloudFront + S3 | ~ |
| NAT Gateway | ~ |
| **Total** | **~/month** |
