import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Bedrock model IDs (cross-region inference profiles)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", ANTHROPIC_MODEL)
RESEARCH_MODEL = os.environ.get("RESEARCH_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

ENGINEER_TIMEOUT = int(os.environ.get("ENGINEER_TIMEOUT", "1200"))  # 20 min
SCIENTIST_TIMEOUT = int(os.environ.get("SCIENTIST_TIMEOUT", "1200"))  # 20 min
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))  # seconds
HEARTBEAT_DEAD_AFTER = HEARTBEAT_INTERVAL * 3  # 90s = presumed dead

SERVER_PORT = int(os.environ.get("SERVER_PORT", "8420"))
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
DATA_DIR = os.environ.get("DATA_DIR", "data")

AMI_ID = os.environ.get("AMI_ID", "")
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "c5.2xlarge")
IAM_INSTANCE_PROFILE = os.environ.get("IAM_INSTANCE_PROFILE", "research-agent-role")
