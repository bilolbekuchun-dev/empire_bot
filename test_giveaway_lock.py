import asyncio
import sys
import os

# Add the project root to sys.path to allow imports
sys.path.append(os.getcwd())

from utils.giveaways_redis import is_processing, mark_as_processing, unmark_as_processing

async def simulate_participation(giveaway_id, user_id, delay=0.1):
    print(f"User {user_id} attempting to participate in Giveaway {giveaway_id}...")
    
    if is_processing(giveaway_id, user_id):
        print(f"User {user_id} BLOCKED: already processing.")
        return False
    
    mark_as_processing(giveaway_id, user_id)
    print(f"User {user_id} LOCKED: starting processing...")
    
    try:
        # Simulate some async work (DB, API calls)
        await asyncio.sleep(delay)
        print(f"User {user_id} SUCCESS: participation recorded.")
        return True
    finally:
        unmark_as_processing(giveaway_id, user_id)
        print(f"User {user_id} UNLOCKED: processing finished.")

async def main():
    giveaway_id = 999
    user_id = 12345
    
    print("--- Test 1: Sequential Participation ---")
    await simulate_participation(giveaway_id, user_id)
    await simulate_participation(giveaway_id, user_id)
    
    print("\n--- Test 2: Concurrent Participation (Rapid Clicking) ---")
    # Simulate 3 rapid clicks at once
    results = await asyncio.gather(
        simulate_participation(giveaway_id, user_id),
        simulate_participation(giveaway_id, user_id),
        simulate_participation(giveaway_id, user_id)
    )
    
    success_count = sum(1 for r in results if r)
    print(f"\nConcurrent success count: {success_count} (Expected: 1)")

if __name__ == "__main__":
    asyncio.run(main())
