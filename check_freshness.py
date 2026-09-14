"""
CLI Entrypoint for PulseNews Freshness Sub-Agent
Usage:
    python check_freshness.py
    python check_freshness.py --auto-fix
    python check_freshness.py --json
"""

import asyncio
import json
import sys
from services.freshness_agent import freshness_agent

async def main():
    auto_fix = "--auto-fix" in sys.argv
    as_json = "--json" in sys.argv
    no_probe = "--no-probe" in sys.argv

    report = await freshness_agent.check_all_sources(
        probe_live=not no_probe,
        auto_fix=auto_fix
    )

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        freshness_agent.print_terminal_report(report)

if __name__ == "__main__":
    asyncio.run(main())
