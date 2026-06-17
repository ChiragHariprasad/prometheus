variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production"
  }
}

variable "region" {
  description = "AWS region for infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Must be a valid IPv4 CIDR block"
  }
}

variable "db_password" {
  description = "Master password for RDS Aurora PostgreSQL"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Auth token for ElastiCache Redis"
  type        = string
  sensitive   = true
  default     = null
}

variable "kafka_instance_type" {
  description = "Instance type for MSK Kafka brokers"
  type        = string
  default     = "kafka.t3.large"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS node groups"
  type = object({
    cpu  = list(string)
    gpu  = list(string)
    spot = list(string)
  })
  default = {
    cpu  = ["m6i.large", "m6i.xlarge"]
    gpu  = ["g5.xlarge", "g4dn.xlarge"]
    spot = ["m6i.large", "c6i.large", "r6i.large"]
  }
}

variable "cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.30"

  validation {
    condition     = can(regex("^1\\.(2[4-9]|30)", var.cluster_version))
    error_message = "Cluster version must be 1.24 or later"
  }
}

variable "tags" {
  description = "Default tags for all AWS resources"
  type        = map(string)
  default = {
    Project     = "PROMETHEUS"
    Environment = "production"
    ManagedBy   = "Terraform"
    Owner       = "PlatformEngineering"
    CostCenter  = "AI-Infrastructure"
  }
}

variable "domain_name" {
  description = "Domain name for Route53 hosted zone"
  type        = string
  default     = "prometheus.io"
}

variable "db_instance_class" {
  description = "Instance class for Aurora serverless"
  type        = string
  default     = "db.serverless"
}

variable "redis_node_type" {
  description = "Node type for ElastiCache Redis cluster"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_shards" {
  description = "Number of Redis shards"
  type        = number
  default     = 3
}

variable "redis_replicas_per_shard" {
  description = "Number of replicas per Redis shard"
  type        = number
  default     = 2
}
