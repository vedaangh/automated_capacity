"""EC2 instance spawning for agent runs.

Two modes:
  - AMI mode: AMI_ID is set, agent code is pre-baked into the image
  - S3 mode: AGENT_CODE_S3 is set, stock Ubuntu AMI + code pulled from S3 at boot

S3 mode is slower (~2 min cold start) but doesn't require rebuilding AMIs.
"""

from __future__ import annotations

import base64
import json
import os

import boto3

from shared.config import AMI_ID, AWS_REGION, IAM_INSTANCE_PROFILE

# Stock Ubuntu 22.04 AMIs (x86_64, hvm-ssd) by region
STOCK_UBUNTU_AMIS = {
    "us-east-1": "ami-0c7217cdde317cfec",
    "us-west-2": "ami-03f65b8614a860c29",
}

AGENT_CODE_S3 = os.environ.get("AGENT_CODE_S3", "")  # e.g. s3://bucket/agent-code.tar.gz


def _build_user_data_s3(payload_json: str) -> str:
    """User-data for S3 mode: install deps + pull code at boot."""
    return f"""#!/bin/bash
set -e
exec > /var/log/agent-boot.log 2>&1

echo "[boot] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3-pip git curl jq ripgrep build-essential

echo "[boot] Installing Python packages..."
pip3 install anthropic httpx pydantic aiofiles boto3

echo "[boot] Pulling agent code from S3..."
aws s3 cp {AGENT_CODE_S3} /tmp/agent-code.tar.gz
mkdir -p /opt/agent
tar xzf /tmp/agent-code.tar.gz -C /opt/agent
rm /tmp/agent-code.tar.gz

echo "[boot] Writing payload..."
cat > /opt/agent/payload.json << 'PAYLOAD_END'
{payload_json}
PAYLOAD_END

echo "[boot] Starting agent harness..."
mkdir -p /lab /lab/streams
cd /opt/agent && python3 -m agents.harness --payload /opt/agent/payload.json 2>&1 | tee /var/log/agent.log
EXIT_CODE=$?

echo "[boot] Agent exited with code $EXIT_CODE. Self-terminating..."
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region {AWS_REGION}
"""


def _build_user_data_ami(payload_json: str) -> str:
    """User-data for AMI mode: code is pre-installed, just write payload + run."""
    return f"""#!/bin/bash
set -e
exec > /var/log/agent-boot.log 2>&1

echo "[boot] Writing payload..."
cat > /opt/agent/payload.json << 'PAYLOAD_END'
{payload_json}
PAYLOAD_END

echo "[boot] Starting agent harness..."
mkdir -p /lab /lab/streams
cd /opt/agent && python3 -m agents.harness --payload /opt/agent/payload.json 2>&1 | tee /var/log/agent.log
EXIT_CODE=$?

echo "[boot] Agent exited with code $EXIT_CODE. Self-terminating..."
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region {AWS_REGION}
"""


async def spawn_agent_ec2(
    run_id: str,
    payload_json: str,
    instance_type: str = "c5.2xlarge",
) -> str:
    """Launch an EC2 instance with the agent harness.

    Uses AMI mode if AMI_ID is set, otherwise S3 mode if AGENT_CODE_S3 is set.
    Returns the instance ID.
    """
    ec2 = boto3.client("ec2", region_name=AWS_REGION)

    # Determine AMI and user-data
    if AMI_ID:
        ami = AMI_ID
        user_data = _build_user_data_ami(payload_json)
    elif AGENT_CODE_S3:
        ami = STOCK_UBUNTU_AMIS.get(AWS_REGION, "")
        if not ami:
            raise ValueError(f"No stock Ubuntu AMI configured for region {AWS_REGION}")
        user_data = _build_user_data_s3(payload_json)
    else:
        raise ValueError(
            "Either AMI_ID or AGENT_CODE_S3 must be set. "
            "AMI_ID for pre-baked images, AGENT_CODE_S3 for boot-time install."
        )

    response = ec2.run_instances(
        ImageId=ami,
        InstanceType=instance_type,
        MinCount=1,
        MaxCount=1,
        UserData=base64.b64encode(user_data.encode()).decode(),
        IamInstanceProfile={"Name": IAM_INSTANCE_PROFILE},
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"research-agent-{run_id[:8]}"},
                    {"Key": "ManagedBy", "Value": "research-system"},
                    {"Key": "RunId", "Value": run_id},
                ],
            }
        ],
    )

    instance_id = response["Instances"][0]["InstanceId"]
    return instance_id


async def upload_agent_code(bucket: str, key: str = "agent-code.tar.gz") -> str:
    """Upload current agent code to S3. Returns the S3 URI.

    Run this once (or after code changes) before spawning EC2 agents in S3 mode:
        python -c "import asyncio; from infra.aws import upload_agent_code; print(asyncio.run(upload_agent_code('my-bucket')))"
    """
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
        tarball_path = f.name

    # Tar up the agent code (agents/ + shared/ directories, excluding __pycache__)
    subprocess.run(
        ["tar", "czf", tarball_path, "--exclude=__pycache__", "agents/", "shared/"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        check=True,
    )

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.upload_file(tarball_path, bucket, key)
    os.unlink(tarball_path)

    s3_uri = f"s3://{bucket}/{key}"
    return s3_uri
