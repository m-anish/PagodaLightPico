"""
Simple test script to verify async functionality works on MicroPython.
This can be run to test if the async architecture will work before deploying.
"""

import asyncio
import time

async def task1():
    """Test task 1"""
    for i in range(5):
        print(f"Task 1: {i}")
        await asyncio.sleep(1)

async def task2():
    """Test task 2"""
    for i in range(3):
        print(f"Task 2: {i}")
        await asyncio.sleep(1.5)

async def main():
    """Main async function"""
    print("Starting async test...")
    
    # Create tasks
    tasks = [
        asyncio.create_task(task1()),
        asyncio.create_task(task2())
    ]
    
    # Run tasks concurrently
    await asyncio.gather(*tasks)
    
    print("Async test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")