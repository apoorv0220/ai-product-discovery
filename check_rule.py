import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from shared.database.base import get_database_session
from sqlalchemy import select
from shared.models.merchandising import MerchandisingRule

async def check_rule():
    async for session in get_database_session():
        result = await session.execute(
            select(MerchandisingRule).where(MerchandisingRule.id == 10)  # Use the latest rule ID
        )
        rule = result.scalar_one_or_none()
        if rule:
            print(f"Rule ID: {rule.id}")
            print(f"Rule Type: {rule.rule_type}")
            print(f"Trigger Conditions: {rule.trigger_conditions}")
            print(f"Target Conditions: {rule.target_conditions}")
            print(f"Conditions: {rule.conditions}")
            print(f"Action Config: {rule.action_config}")
        else:
            print("Rule not found")

if __name__ == "__main__":
    asyncio.run(check_rule())

