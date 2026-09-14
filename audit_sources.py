"""
CLI entry point for PulseNews Source Audit Sub-Agent
Usage:
    python audit_sources.py
"""
import asyncio
from services.audit_agent import audit_agent

if __name__ == "__main__":
    asyncio.run(audit_agent.run_full_audit(auto_fix=True))
