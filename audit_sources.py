"""
CLI entry point for PulseNews Source & Freshness Audit Sub-Agents
Usage:
    python audit_sources.py              # Full QA & Freshness audit
    python audit_sources.py --freshness  # Freshness audit only
"""
import asyncio
import sys
from services.audit_agent import audit_agent
from services.freshness_agent import freshness_agent

async def main():
    if "--freshness" in sys.argv:
        report = await freshness_agent.check_all_sources(probe_live=True, auto_fix=False)
        freshness_agent.print_terminal_report(report)
    else:
        # Run structural & matrix audit
        await audit_agent.run_full_audit(auto_fix=True)
        # Run real-time freshness audit
        print("\n" + "=" * 70)
        print("  TRIGGERING SUB-AGENT: REAL-TIME SOURCE FRESHNESS AUDIT")
        print("=" * 70)
        fresh_report = await freshness_agent.check_all_sources(probe_live=True, auto_fix=False)
        freshness_agent.print_terminal_report(fresh_report)

if __name__ == "__main__":
    asyncio.run(main())
