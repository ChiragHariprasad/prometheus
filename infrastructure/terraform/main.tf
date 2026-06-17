terraform {
  required_version = ">= 1.5.0"
}

provider "aws" {
  region  = var.region
  version = "~> 5.0"
  default_tags {
    tags = var.tags
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.environment}-prometheus-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-prometheus-igw"
  }
}

resource "aws_eip" "nat" {
  count  = 3
  domain = "vpc"

  tags = {
    Name = "${var.environment}-prometheus-nat-eip-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "main" {
  count         = 3
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.environment}-prometheus-nat-${count.index + 1}"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                          = "${var.environment}-prometheus-public-${count.index + 1}"
    "kubernetes.io/cluster/${var.environment}-prometheus-eks" = "shared"
    "kubernetes.io/role/elb"                      = "1"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 3)
  availability_zone = local.azs[count.index]

  tags = {
    Name                                          = "${var.environment}-prometheus-private-${count.index + 1}"
    "kubernetes.io/cluster/${var.environment}-prometheus-eks" = "shared"
    "kubernetes.io/role/internal-elb"             = "1"
  }
}

# Database Subnets
resource "aws_subnet" "database" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 6)
  availability_zone = local.azs[count.index]

  tags = {
    Name = "${var.environment}-prometheus-db-${count.index + 1}"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.environment}-prometheus-public-rt"
  }
}

resource "aws_route_table" "private" {
  count  = 3
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "${var.environment}-prometheus-private-rt-${count.index + 1}"
  }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# VPC Endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.region}.s3"
  route_table_ids = flatten([
    aws_route_table.public.id,
    aws_route_table.private[*].id
  ])

  tags = {
    Name = "${var.environment}-prometheus-s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.region}.dynamodb"
  route_table_ids = flatten([
    aws_route_table.public.id,
    aws_route_table.private[*].id
  ])

  tags = {
    Name = "${var.environment}-prometheus-dynamodb-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.environment}-prometheus-ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.environment}-prometheus-ecr-dkr-endpoint"
  }
}

# Security Groups
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.environment}-prometheus-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "HTTPS from VPC"
  }

  tags = {
    Name = "${var.environment}-prometheus-vpc-endpoints-sg"
  }
}

resource "aws_security_group" "cluster" {
  name        = "${var.environment}-prometheus-eks-cluster-sg"
  description = "Security group for EKS cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Kubernetes API server"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-prometheus-eks-cluster-sg"
  }
}

resource "aws_security_group" "node" {
  name        = "${var.environment}-prometheus-eks-node-sg"
  description = "Security group for EKS node groups"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
    description = "Cluster internal communication"
  }

  ingress {
    from_port   = 10250
    to_port     = 10250
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "kubelet API"
  }

  ingress {
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "NodePort services"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-prometheus-eks-node-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.environment}-prometheus-rds-sg"
  description = "Security group for RDS Aurora"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.node.id]
    description     = "PostgreSQL from EKS nodes"
  }

  tags = {
    Name = "${var.environment}-prometheus-rds-sg"
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.environment}-prometheus-redis-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.node.id]
    description     = "Redis from EKS nodes"
  }

  tags = {
    Name = "${var.environment}-prometheus-redis-sg"
  }
}

resource "aws_security_group" "kafka" {
  name        = "${var.environment}-prometheus-kafka-sg"
  description = "Security group for MSK Kafka"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 9092
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.node.id]
    description     = "Kafka from EKS nodes"
  }

  ingress {
    from_port       = 2181
    to_port         = 2181
    protocol        = "tcp"
    security_groups = [aws_security_group.node.id]
    description     = "ZooKeeper from EKS nodes"
  }

  tags = {
    Name = "${var.environment}-prometheus-kafka-sg"
  }
}

# S3 Buckets
resource "aws_s3_bucket" "twin_snapshots" {
  bucket = "${var.environment}-prometheus-twin-snapshots"
  force_destroy = false
}

resource "aws_s3_bucket" "event_archive" {
  bucket = "${var.environment}-prometheus-event-archive"
  force_destroy = false
}

resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.environment}-prometheus-model-artifacts"
  force_destroy = false
}

resource "aws_s3_bucket" "exports" {
  bucket = "${var.environment}-prometheus-exports"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "twin_snapshots" {
  bucket = aws_s3_bucket.twin_snapshots.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "event_archive" {
  bucket = aws_s3_bucket.event_archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "twin_snapshots" {
  bucket = aws_s3_bucket.twin_snapshots.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "event_archive" {
  bucket = aws_s3_bucket.event_archive.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "twin_snapshots" {
  bucket                  = aws_s3_bucket.twin_snapshots.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "event_archive" {
  bucket                  = aws_s3_bucket.event_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "model_artifacts" {
  bucket                  = aws_s3_bucket.model_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "exports" {
  bucket                  = aws_s3_bucket.exports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# EKS Cluster
resource "aws_iam_role" "eks_cluster" {
  name = "${var.environment}-prometheus-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_eks_cluster" "main" {
  name     = "${var.environment}-prometheus-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = flatten([aws_subnet.public[*].id, aws_subnet.private[*].id])
    security_group_ids      = [aws_security_group.cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]
}

# KMS Key for EKS
resource "aws_kms_key" "eks" {
  description             = "${var.environment}-prometheus-eks-encryption-key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.environment}-prometheus-eks-kms"
  }
}

resource "aws_kms_key" "rds" {
  description             = "${var.environment}-prometheus-rds-encryption-key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.environment}-prometheus-rds-kms"
  }
}

# EKS Node IAM Role
resource "aws_iam_role" "eks_node" {
  name = "${var.environment}-prometheus-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "ssm_managed" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.eks_node.name
}

# CPU Node Group
resource "aws_eks_node_group" "cpu" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-prometheus-cpu"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id

  instance_types = var.node_instance_types.cpu

  scaling_config {
    desired_size = 3
    min_size     = 1
    max_size     = 10
  }

  capacity_type = "ON_DEMAND"

  update_config {
    max_unavailable = 1
  }

  labels = {
    "nodegroup-type" = "cpu"
    "workload"       = "general"
  }

  tags = {
    Name = "${var.environment}-prometheus-cpu-node-group"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_readonly,
  ]
}

# GPU Node Group
resource "aws_eks_node_group" "gpu" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-prometheus-gpu"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id

  instance_types = var.node_instance_types.gpu

  scaling_config {
    desired_size = 1
    min_size     = 0
    max_size     = 5
  }

  capacity_type = "ON_DEMAND"

  update_config {
    max_unavailable = 1
  }

  labels = {
    "nodegroup-type" = "gpu"
    "workload"       = "ml-inference"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  tags = {
    Name = "${var.environment}-prometheus-gpu-node-group"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_readonly,
  ]
}

# Spot Node Group
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-prometheus-spot"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id

  instance_types = var.node_instance_types.spot

  scaling_config {
    desired_size = 2
    min_size     = 0
    max_size     = 20
  }

  capacity_type = "SPOT"

  update_config {
    max_unavailable = 1
  }

  labels = {
    "nodegroup-type" = "spot"
    "workload"       = "batch"
  }

  tags = {
    Name = "${var.environment}-prometheus-spot-node-group"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_readonly,
  ]
}

# RDS Aurora PostgreSQL
resource "aws_rds_cluster" "aurora" {
  cluster_identifier          = "${var.environment}-prometheus-aurora"
  engine                      = "aurora-postgresql"
  engine_mode                 = "provisioned"
  engine_version             = "15.4"
  database_name              = "prometheus"
  master_username            = "prometheus_admin"
  master_password            = var.db_password
  port                       = 5432
  vpc_security_group_ids     = [aws_security_group.rds.id]
  db_subnet_group_name       = aws_db_subnet_group.aurora.name
  backup_retention_period    = 30
  preferred_backup_window    = "03:00-04:00"
  preferred_maintenance_window = "sun:05:00-sun:06:00"
  deletion_protection        = true
  skip_final_snapshot       = false
  final_snapshot_identifier  = "${var.environment}-prometheus-aurora-final-snapshot"
  storage_encrypted         = true
  kms_key_id                = aws_kms_key.rds.arn
  copy_tags_to_snapshot     = true
  enabled_cloudwatch_logs_exports = ["postgresql"]

  serverlessv2_scaling_configuration {
    min_capacity = 1
    max_capacity = 16
  }

  tags = {
    Name = "${var.environment}-prometheus-aurora"
  }
}

resource "aws_rds_cluster_instance" "aurora_instances" {
  count              = 2
  identifier         = "${var.environment}-prometheus-aurora-instance-${count.index + 1}"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version
  db_subnet_group_name = aws_db_subnet_group.aurora.name
  publicly_accessible  = false

  tags = {
    Name = "${var.environment}-prometheus-aurora-instance-${count.index + 1}"
  }
}

resource "aws_db_subnet_group" "aurora" {
  name        = "${var.environment}-prometheus-aurora-subnet-group"
  subnet_ids  = aws_subnet.database[*].id

  tags = {
    Name = "${var.environment}-prometheus-aurora-subnet-group"
  }
}

# IAM Role for RDS
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.environment}-prometheus-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring.name
}

resource "aws_db_parameter_group" "aurora" {
  name        = "${var.environment}-prometheus-aurora-params"
  family      = "aurora-postgresql15"

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "${var.environment}-prometheus-aurora-params"
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "redis" {
  name        = "${var.environment}-prometheus-redis-subnet-group"
  subnet_ids  = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.environment}-prometheus-redis"
  description                   = "PROMETHEUS Redis cluster"
  engine                        = "redis"
  engine_version                = "7.1"
  node_type                     = "cache.r6g.large"
  num_cache_clusters            = 3
  port                          = 6379
  parameter_group_name          = aws_elasticache_parameter_group.redis.name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  automatic_failover_enabled    = true
  multi_az_enabled              = true
  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = true
  kms_key_id                   = aws_kms_key.redis.arn
  snapshot_retention_limit     = 7
  snapshot_window              = "02:00-03:00"
  maintenance_window           = "sun:06:00-sun:07:00"
  auto_minor_version_upgrade   = true
  notification_topic_arn       = null

  tags = {
    Name = "${var.environment}-prometheus-redis"
  }
}

resource "aws_elasticache_parameter_group" "redis" {
  name        = "${var.environment}-prometheus-redis-params"
  family      = "redis7"

  parameter {
    name  = "cluster-enabled"
    value = "yes"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = {
    Name = "${var.environment}-prometheus-redis-params"
  }
}

resource "aws_kms_key" "redis" {
  description             = "${var.environment}-prometheus-redis-encryption-key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.environment}-prometheus-redis-kms"
  }
}

# MSK Kafka
resource "aws_msk_cluster" "kafka" {
  cluster_name           = "${var.environment}-prometheus-kafka"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = var.kafka_instance_type
    client_subnets  = aws_subnet.private[*].id
    security_groups = [aws_security_group.kafka.id]
    storage_info {
      ebs_storage_info {
        volume_size = 300
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.kafka.arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    sasl {
      iam = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka.name
      }
    }
  }

  enhanced_monitoring = "PER_TOPIC_PER_PARTITION"

  tags = {
    Name = "${var.environment}-prometheus-kafka"
  }
}

resource "aws_kms_key" "kafka" {
  description             = "${var.environment}-prometheus-kafka-encryption-key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.environment}-prometheus-kafka-kms"
  }
}

resource "aws_cloudwatch_log_group" "kafka" {
  name              = "/aws/msk/${var.environment}-prometheus-kafka"
  retention_in_days = 30

  tags = {
    Name = "${var.environment}-prometheus-kafka-logs"
  }
}

# IAM Role for Service Accounts (IRSA)
resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_role" "service_accounts" {
  name = "${var.environment}-prometheus-sa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:default:prometheus-backend"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "service_accounts" {
  name = "${var.environment}-prometheus-sa-policy"
  role = aws_iam_role.service_accounts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject",
        ]
        Resource = [
          aws_s3_bucket.twin_snapshots.arn,
          "${aws_s3_bucket.twin_snapshots.arn}/*",
          aws_s3_bucket.event_archive.arn,
          "${aws_s3_bucket.event_archive.arn}/*",
          aws_s3_bucket.model_artifacts.arn,
          "${aws_s3_bucket.model_artifacts.arn}/*",
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kafka:DescribeCluster",
          "kafka:GetBootstrapBrokers",
          "kafka:DescribeClusterV2",
        ]
        Resource = [aws_msk_cluster.kafka.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:BatchGetImage",
        ]
        Resource = ["*"]
      },
    ]
  })
}

# Route53
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "api.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.api.dns_name]
}

resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "app.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.frontend.dns_name]
}

# ACM Certificates
resource "aws_acm_certificate" "api" {
  domain_name       = "api.${var.domain_name}"
  validation_method = "DNS"

  tags = {
    Name = "${var.environment}-prometheus-api-cert"
  }
}

resource "aws_acm_certificate" "app" {
  domain_name       = "app.${var.domain_name}"
  validation_method = "DNS"

  tags = {
    Name = "${var.environment}-prometheus-app-cert"
  }
}

resource "aws_acm_certificate" "wildcard" {
  domain_name       = "*.${var.domain_name}"
  validation_method = "DNS"

  tags = {
    Name = "${var.environment}-prometheus-wildcard-cert"
  }
}

resource "aws_route53_record" "cert_validation_api" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_route53_record" "cert_validation_app" {
  for_each = {
    for dvo in aws_acm_certificate.app.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_route53_record" "cert_validation_wildcard" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_api : record.fqdn]
}

resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_app : record.fqdn]
}

resource "aws_acm_certificate_validation" "wildcard" {
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_wildcard : record.fqdn]
}

# ALB
resource "aws_lb" "api" {
  name               = "${var.environment}-prometheus-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "${var.environment}-prometheus-api-alb"
  }
}

resource "aws_lb" "frontend" {
  name               = "${var.environment}-prometheus-frontend-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "${var.environment}-prometheus-frontend-alb"
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.environment}-prometheus-alb-sg"
  description = "Security group for ALBs"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-prometheus-alb-sg"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "${var.environment}-prometheus-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    timeout             = 5
  }

  tags = {
    Name = "${var.environment}-prometheus-api-tg"
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.environment}-prometheus-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    path                = "/"
    port                = "traffic-port"
    timeout             = 5
  }

  tags = {
    Name = "${var.environment}-prometheus-frontend-tg"
  }
}

resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "api_https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.api.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "frontend_http" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "frontend_https" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.app.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# CloudFront
resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.environment}-prometheus-frontend-cdn"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = ["app.${var.domain_name}"]

  origin {
    domain_name = aws_lb.frontend.dns_name
    origin_id   = "frontend-alb"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "frontend-alb"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Origin", "Authorization", "CloudFront-Forwarded-Proto"]
      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 86400
  }

  ordered_cache_behavior {
    path_pattern           = "/_next/static/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "frontend-alb"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      headers      = []
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 31536000
    max_ttl     = 31536000
  }

  ordered_cache_behavior {
    path_pattern           = "/static/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "frontend-alb"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      headers      = []
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 31536000
    max_ttl     = 31536000
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.app.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name = "${var.environment}-prometheus-frontend-cdn"
  }
}

# WAF
resource "aws_wafv2_web_acl" "api" {
  name        = "${var.environment}-prometheus-api-waf"
  description = "WAF Web ACL for PROMETHEUS API"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAmazonIpReputationList"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimit"
    priority = 5

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 5000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.environment}-prometheus-api-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Name = "${var.environment}-prometheus-api-waf"
  }
}

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.environment}-prometheus-eks"
  retention_in_days = 30

  tags = {
    Name = "${var.environment}-prometheus-eks-logs"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lb/${var.environment}-prometheus-api"
  retention_in_days = 30

  tags = {
    Name = "${var.environment}-prometheus-api-access-logs"
  }
}
