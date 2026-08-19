# Architecture Diagram - FlashSale AWS

## System Architecture

```
User Browser
     |
Route 53 (DNS - samdevops.online)
     |
CloudFront (CDN - Global Edge Caching)
     |
AWS WAF (Firewall - DDoS, SQLi, XSS Protection)
     |
ALB - Application Load Balancer (Public Subnet)
     |          |
EC2 AZ-A    EC2 AZ-B  (Private Subnet - FastAPI Backend)
     |          |
     +----+-----+
          |
    +-----+------+
    |             |
ElastiCache    RDS MySQL
  Redis        Multi-AZ
(Cache Layer) (Data Subnet - Private)
```

## VPC Network Layout
```
VPC: 10.0.0.0/16 (Mumbai ap-south-1)
|
|-- PUBLIC SUBNET A (10.0.1.0/24) - AZ-A
|   [Internet Gateway, ALB, NAT Gateway]
|
|-- PUBLIC SUBNET B (10.0.2.0/24) - AZ-B
|   [ALB node]
|
|-- PRIVATE SUBNET A (10.0.10.0/24) - AZ-A
|   [EC2 Auto Scaling Instances]
|
|-- PRIVATE SUBNET B (10.0.11.0/24) - AZ-B
|   [EC2 Auto Scaling Instances]
|
|-- DATA SUBNET A (10.0.20.0/24) - AZ-A
|   [RDS MySQL Primary, ElastiCache]
|
|-- DATA SUBNET B (10.0.21.0/24) - AZ-B
    [RDS MySQL Standby]
```

## Request Flow
1. User visits samdevops.online
2. Route 53 resolves DNS to CloudFront
3. CloudFront checks edge cache - if HIT, returns immediately
4. If MISS, WAF inspects request for threats
5. ALB distributes to healthy EC2 instance
6. EC2 checks ElastiCache Redis for product data
7. If Redis MISS, fetches from RDS MySQL (Private Subnet)
8. Returns response to user

## Auto Scaling Triggers
- CPU > 70% for 2 minutes -> Add EC2 instances
- CPU < 30% for 5 minutes -> Remove EC2 instances
- Min: 2 instances | Max: 20 instances
