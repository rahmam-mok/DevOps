# AWS CLI — Daily Use Cheat Sheet

A practical reference of the most commonly used AWS CLI commands, with comments
explaining what each does and copy-paste-ready examples.

> **Output formats:** add `--output table|json|text|yaml` to any command.
> **Profiles/Regions:** add `--profile myprofile` or `--region us-east-1` to target a specific account/region.
> **Tip:** append `--dry-run` (where supported) to test permissions without making changes.

---

## 0. Setup, Configuration & Identity

```bash
# Configure default credentials, region, and output format interactively
aws configure

# Configure a NAMED profile (useful for multiple accounts)
aws configure --profile prod

# List all configured profiles
aws configure list-profiles

# Show the current effective config (keys are masked)
aws configure list

# WHO AM I? — confirm which account/user/role your credentials map to.
# This is the #1 sanity-check command before running anything important.
aws sts get-caller-identity
# Example output: Account "123456789012", Arn ".../assumed-role/Admin/you"

# Get a temporary session token (e.g. for MFA-protected actions)
aws sts get-session-token --duration-seconds 3600

# Assume a cross-account / privileged role
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/DeployRole \
  --role-session-name my-session
```

---

## 1. S3 — Object Storage

```bash
# List all buckets in the account
aws s3 ls

# List objects inside a bucket (add a prefix/"folder")
aws s3 ls s3://my-bucket/logs/ --recursive --human-readable --summarize

# Upload a single file
aws s3 cp ./report.pdf s3://my-bucket/reports/report.pdf

# Download a single file
aws s3 cp s3://my-bucket/reports/report.pdf ./report.pdf

# Sync a local directory UP to S3 (only changed/new files transfer)
aws s3 sync ./website/ s3://my-bucket/ --delete   # --delete removes remote files not present locally

# Sync FROM S3 down to local
aws s3 sync s3://my-bucket/backups/ ./backups/

# Remove a single object
aws s3 rm s3://my-bucket/old/file.txt

# Recursively delete a "folder"
aws s3 rm s3://my-bucket/tmp/ --recursive

# Create / delete a bucket
aws s3 mb s3://my-new-bucket --region us-east-1   # make bucket
aws s3 rb s3://my-old-bucket --force              # remove bucket (--force empties it first)

# Generate a temporary pre-signed URL (shareable, expires) — great for private files
aws s3 presign s3://my-bucket/reports/report.pdf --expires-in 3600
```

---

## 2. EC2 — Compute

```bash
# List instances with the columns you actually care about (clean table output)
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,State:State.Name,IP:PublicIpAddress,Name:Tags[?Key==`Name`]|[0].Value}' \
  --output table

# List only RUNNING instances (server-side filter is faster/cheaper than client-side)
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text

# Start / stop / reboot / terminate an instance
aws ec2 start-instances     --instance-ids i-0abc123
aws ec2 stop-instances      --instance-ids i-0abc123
aws ec2 reboot-instances    --instance-ids i-0abc123
aws ec2 terminate-instances --instance-ids i-0abc123   # IRREVERSIBLE

# Launch a new instance from an AMI
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro \
  --key-name my-keypair \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-01}]'

# Describe security groups (firewall rules)
aws ec2 describe-security-groups --group-ids sg-0abc123

# Open port 443 to the world on a security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abc123 --protocol tcp --port 443 --cidr 0.0.0.0/0

# List available AMIs owned by you
aws ec2 describe-images --owners self --query 'Images[].{ID:ImageId,Name:Name}' --output table

# List key pairs and Elastic IPs
aws ec2 describe-key-pairs
aws ec2 describe-addresses
```

---

## 3. IAM — Identity & Access Management

```bash
# List users, roles, groups
aws iam list-users
aws iam list-roles
aws iam list-groups

# Show policies attached to a user
aws iam list-attached-user-policies --user-name alice

# Create a user and an access key
aws iam create-user --user-name alice
aws iam create-access-key --user-name alice   # SAVE the secret — shown only once!

# Attach a managed policy to a user
aws iam attach-user-policy --user-name alice \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# List all managed policies (AWS-managed + customer)
aws iam list-policies --scope Local   # Local = only your custom policies

# View a role's trust/permissions
aws iam get-role --role-name DeployRole

# Generate a credential report (CSV of all users, last-used, MFA status)
aws iam generate-credential-report
aws iam get-credential-report --query Content --output text | base64 -d
```

---

## 4. Lambda — Serverless Functions

```bash
# List functions
aws lambda list-functions --query 'Functions[].FunctionName' --output table

# Invoke a function synchronously and capture the response
aws lambda invoke \
  --function-name my-func \
  --payload '{"key":"value"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json

# Update function code from a local zip
aws lambda update-function-code \
  --function-name my-func \
  --zip-file fileb://function.zip

# Update environment variables / config
aws lambda update-function-configuration \
  --function-name my-func \
  --timeout 30 --memory-size 256 \
  --environment "Variables={STAGE=prod,LOG_LEVEL=info}"

# View recent config and last update status
aws lambda get-function-configuration --function-name my-func
```

---

## 5. CloudWatch Logs — Debugging & Monitoring

```bash
# List log groups
aws logs describe-log-groups --query 'logGroups[].logGroupName' --output table

# TAIL logs live (like `tail -f`) — extremely handy for debugging
aws logs tail /aws/lambda/my-func --follow

# Tail with a time window and filter pattern
aws logs tail /aws/lambda/my-func --since 1h --filter-pattern "ERROR"

# Query metrics (e.g. EC2 CPU) — get average CPU over the last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time   $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

---

## 6. RDS — Managed Databases

```bash
# List DB instances with key info
aws rds describe-db-instances \
  --query 'DBInstances[].{ID:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus,Endpoint:Endpoint.Address}' \
  --output table

# Create a manual snapshot (backup) before a risky change
aws rds create-db-snapshot \
  --db-instance-identifier mydb --db-snapshot-identifier mydb-before-migration

# Start / stop a DB instance (saves cost in non-prod)
aws rds start-db-instance --db-instance-identifier mydb
aws rds stop-db-instance  --db-instance-identifier mydb
```

---

## 7. ECR & ECS — Containers

```bash
# --- ECR (container registry) ---
# Authenticate Docker to your ECR registry (pipe login into docker)
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# List repositories and images
aws ecr describe-repositories
aws ecr list-images --repository-name my-app

# --- ECS (container orchestration) ---
# List clusters / services
aws ecs list-clusters
aws ecs list-services --cluster my-cluster

# Force a new deployment (e.g. after pushing a new image with the same tag)
aws ecs update-service --cluster my-cluster --service my-svc --force-new-deployment

# Check running tasks
aws ecs list-tasks --cluster my-cluster --service-name my-svc
```

---

## 8. Secrets Manager & SSM Parameter Store

```bash
# --- Secrets Manager (rotating secrets, DB creds) ---
aws secretsmanager get-secret-value --secret-id prod/db/password --query SecretString --output text
aws secretsmanager list-secrets --query 'SecretList[].Name'

# --- SSM Parameter Store (config + secrets, cheaper) ---
# Read a parameter (use --with-decryption for SecureString types)
aws ssm get-parameter --name /app/prod/api-key --with-decryption --query Parameter.Value --output text

# Write a parameter
aws ssm put-parameter --name /app/prod/api-key --value "s3cr3t" --type SecureString --overwrite

# Get all params under a path (great for loading app config)
aws ssm get-parameters-by-path --path /app/prod/ --with-decryption --recursive

# Start an interactive shell on an EC2 instance — NO SSH keys / open ports needed!
aws ssm start-session --target i-0abc123
```

---

## 9. DynamoDB

```bash
# List tables
aws dynamodb list-tables

# Get a single item by primary key
aws dynamodb get-item --table-name Users \
  --key '{"userId": {"S": "u-123"}}'

# Put (insert/replace) an item
aws dynamodb put-item --table-name Users \
  --item '{"userId": {"S": "u-123"}, "name": {"S": "Alice"}}'

# Scan a whole table (use sparingly on large tables — it's expensive)
aws dynamodb scan --table-name Users --max-items 25
```

---

## 10. Universal Power Tips

```bash
# --query : filter/reshape output with JMESPath (client-side, works on any command)
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'

# --filters : server-side filtering (faster, preferred when available)
aws ec2 describe-instances --filters "Name=tag:Environment,Values=prod"

# --output text + shell = scripting glue. Example: stop ALL running instances
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text \
  | xargs aws ec2 stop-instances --instance-ids

# Built-in help for ANY command (no internet needed)
aws ec2 describe-instances help

# See which CLI version you're running
aws --version

# Paginate manually for huge result sets
aws s3api list-objects-v2 --bucket my-bucket --max-items 100 --starting-token <token>
```

---

### Quick safety reminders
- `terminate-instances`, `rb --force`, `rm --recursive`, and `delete-*` are **irreversible** — double-check the target and `--profile`.
- Always run `aws sts get-caller-identity` first when switching accounts.
- Prefer `--filters` (server-side) over `--query` (client-side) for large datasets.
