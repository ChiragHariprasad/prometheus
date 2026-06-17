output "cluster_endpoint" {
  description = "EKS cluster API server endpoint"
  value       = aws_eks_cluster.main.endpoint
  sensitive   = false
}

output "cluster_ca_certificate" {
  description = "Base64-encoded certificate data for EKS cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "cluster_security_group_id" {
  description = "Security group ID attached to EKS cluster"
  value       = aws_security_group.cluster.id
}

output "rds_endpoint" {
  description = "RDS Aurora writer endpoint"
  value       = aws_rds_cluster.aurora.endpoint
  sensitive   = false
}

output "rds_reader_endpoint" {
  description = "RDS Aurora reader endpoint"
  value       = aws_rds_cluster.aurora.reader_endpoint
  sensitive   = false
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = false
}

output "redis_reader_endpoint" {
  description = "ElastiCache Redis reader endpoint"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
  sensitive   = false
}

output "kafka_bootstrap_brokers" {
  description = "Kafka bootstrap brokers TLS connection string"
  value       = aws_msk_cluster.kafka.bootstrap_brokers_tls
  sensitive   = true
}

output "kafka_zookeeper_connect" {
  description = "Kafka ZooKeeper connection string"
  value       = aws_msk_cluster.kafka.zookeeper_connect_string
  sensitive   = true
}

output "s3_bucket_names" {
  description = "Map of S3 bucket names by purpose"
  value = {
    twin_snapshots  = aws_s3_bucket.twin_snapshots.id
    event_archive   = aws_s3_bucket.event_archive.id
    model_artifacts = aws_s3_bucket.model_artifacts.id
    exports         = aws_s3_bucket.exports.id
  }
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_node_role_arn" {
  description = "IAM role ARN for EKS node groups"
  value       = aws_iam_role.eks_node.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "waf_acl_id" {
  description = "WAF Web ACL ID"
  value       = aws_wafv2_web_acl.api.id
}

output "alb_api_dns" {
  description = "API ALB DNS name"
  value       = aws_lb.api.dns_name
}

output "alb_frontend_dns" {
  description = "Frontend ALB DNS name"
  value       = aws_lb.frontend.dns_name
}

output "iam_service_account_role_arn" {
  description = "IAM role ARN for Kubernetes service accounts"
  value       = aws_iam_role.service_accounts.arn
}
