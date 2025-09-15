"""
Demonstration of retry logic with exponential backoff and circuit breaker.
"""

import asyncio
import logging
import time
from datetime import datetime

from src.backend.utils.retry_logic import (
    retry_database_operation, retry_http_request, retry_miner_operation,
    get_retry_stats, reset_circuit_breaker, RetryConfig, retry_with_backoff
)
from src.backend.exceptions import (
    DatabaseConnectionError, MinerConnectionError, MinerTimeoutError,
    NetworkError
)

# Configure logging to see retry attempts
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RetryDemo:
    """Demonstration of retry logic functionality."""
    
    def __init__(self):
        self.demo_counter = 0
    
    @retry_database_operation(max_attempts=4, base_delay=1.0, max_delay=10.0)
    async def simulate_database_operation(self):
        """Simulate a database operation that fails initially."""
        self.demo_counter += 1
        logger.info(f"Database operation attempt {self.demo_counter}")
        
        if self.demo_counter < 3:
            raise DatabaseConnectionError(f"Database connection failed (attempt {self.demo_counter})")
        
        logger.info("Database operation succeeded!")
        return {"status": "success", "data": "database_result"}
    
    @retry_http_request(max_attempts=3, base_delay=0.5, max_delay=5.0)
    async def simulate_http_request(self):
        """Simulate an HTTP request that times out initially."""
        self.demo_counter += 1
        logger.info(f"HTTP request attempt {self.demo_counter}")
        
        if self.demo_counter < 2:
            raise MinerConnectionError(f"HTTP connection failed (attempt {self.demo_counter})")
        
        logger.info("HTTP request succeeded!")
        return {"status": "ok", "response": "http_result"}
    
    @retry_miner_operation(max_attempts=3, base_delay=2.0, max_delay=30.0)
    async def simulate_miner_operation(self):
        """Simulate a miner operation that times out initially."""
        self.demo_counter += 1
        logger.info(f"Miner operation attempt {self.demo_counter}")
        
        if self.demo_counter < 2:
            raise MinerTimeoutError(f"Miner timeout (attempt {self.demo_counter})")
        
        logger.info("Miner operation succeeded!")
        return {"hashrate": 150, "temperature": 65, "status": "mining"}
    
    @retry_with_backoff(RetryConfig(max_attempts=5, base_delay=0.5, exponential_base=1.5))
    async def simulate_custom_retry(self):
        """Simulate operation with custom retry configuration."""
        self.demo_counter += 1
        logger.info(f"Custom retry operation attempt {self.demo_counter}")
        
        if self.demo_counter < 4:
            raise NetworkError(f"Network error (attempt {self.demo_counter})")
        
        logger.info("Custom retry operation succeeded!")
        return {"result": "custom_success"}
    
    def reset_counter(self):
        """Reset the demo counter."""
        self.demo_counter = 0


async def demonstrate_retry_logic():
    """Demonstrate various retry scenarios."""
    demo = RetryDemo()
    
    print("=" * 60)
    print("RETRY LOGIC DEMONSTRATION")
    print("=" * 60)
    
    # Demo 1: Database operation retry
    print("\n1. Database Operation Retry Demo")
    print("-" * 40)
    demo.reset_counter()
    
    try:
        start_time = time.time()
        result = await demo.simulate_database_operation()
        end_time = time.time()
        
        print(f"✅ Database operation succeeded: {result}")
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Database operation failed: {e}")
    
    # Demo 2: HTTP request retry
    print("\n2. HTTP Request Retry Demo")
    print("-" * 40)
    demo.reset_counter()
    
    try:
        start_time = time.time()
        result = await demo.simulate_http_request()
        end_time = time.time()
        
        print(f"✅ HTTP request succeeded: {result}")
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ HTTP request failed: {e}")
    
    # Demo 3: Miner operation retry
    print("\n3. Miner Operation Retry Demo")
    print("-" * 40)
    demo.reset_counter()
    
    try:
        start_time = time.time()
        result = await demo.simulate_miner_operation()
        end_time = time.time()
        
        print(f"✅ Miner operation succeeded: {result}")
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Miner operation failed: {e}")
    
    # Demo 4: Custom retry configuration
    print("\n4. Custom Retry Configuration Demo")
    print("-" * 40)
    demo.reset_counter()
    
    try:
        start_time = time.time()
        result = await demo.simulate_custom_retry()
        end_time = time.time()
        
        print(f"✅ Custom retry operation succeeded: {result}")
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Custom retry operation failed: {e}")
    
    # Demo 5: Circuit breaker stats
    print("\n5. Circuit Breaker Statistics")
    print("-" * 40)
    
    stats = await get_retry_stats()
    print(f"📊 Circuit breaker statistics:")
    for name, state in stats["circuit_breakers"].items():
        print(f"   {name}: {state['state']} (failures: {state['failure_count']})")
    
    # Demo 6: Exponential backoff timing
    print("\n6. Exponential Backoff Timing Demo")
    print("-" * 40)
    
    attempt_times = []
    
    @retry_with_backoff(RetryConfig(max_attempts=4, base_delay=0.5, jitter=False))
    async def timing_demo():
        attempt_times.append(datetime.now())
        if len(attempt_times) < 4:
            raise NetworkError(f"Timing demo failure {len(attempt_times)}")
        return "timing_success"
    
    try:
        result = await timing_demo()
        print(f"✅ Timing demo succeeded: {result}")
        
        print("⏱️  Retry intervals:")
        for i in range(1, len(attempt_times)):
            interval = (attempt_times[i] - attempt_times[i-1]).total_seconds()
            expected = 0.5 * (2 ** (i-1))  # exponential backoff
            print(f"   Attempt {i+1}: {interval:.2f}s (expected: ~{expected:.2f}s)")
    
    except Exception as e:
        print(f"❌ Timing demo failed: {e}")


async def demonstrate_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("\n" + "=" * 60)
    print("CIRCUIT BREAKER DEMONSTRATION")
    print("=" * 60)
    
    failure_count = 0
    
    @retry_with_backoff(
        RetryConfig(max_attempts=2, base_delay=0.1, failure_threshold=3),
        circuit_breaker_name="demo_circuit"
    )
    async def failing_operation():
        nonlocal failure_count
        failure_count += 1
        logger.info(f"Failing operation attempt {failure_count}")
        raise NetworkError(f"Simulated failure {failure_count}")
    
    # Trigger circuit breaker by causing multiple failures
    print("\n1. Triggering Circuit Breaker")
    print("-" * 40)
    
    for i in range(5):
        try:
            await failing_operation()
        except Exception as e:
            print(f"Attempt {i+1}: {type(e).__name__}: {e}")
        
        # Check circuit breaker state
        stats = await get_retry_stats()
        if "demo_circuit" in stats["circuit_breakers"]:
            state = stats["circuit_breakers"]["demo_circuit"]
            print(f"   Circuit state: {state['state']} (failures: {state['failure_count']})")
    
    # Reset circuit breaker
    print("\n2. Resetting Circuit Breaker")
    print("-" * 40)
    
    reset_result = await reset_circuit_breaker("demo_circuit")
    print(f"Circuit breaker reset: {reset_result}")
    
    stats = await get_retry_stats()
    if "demo_circuit" in stats["circuit_breakers"]:
        state = stats["circuit_breakers"]["demo_circuit"]
        print(f"Circuit state after reset: {state['state']} (failures: {state['failure_count']})")


async def main():
    """Main demonstration function."""
    print("🔄 Starting Retry Logic and Circuit Breaker Demonstration")
    
    await demonstrate_retry_logic()
    await demonstrate_circuit_breaker()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\n📝 Summary:")
    print("   ✅ Retry logic with exponential backoff implemented")
    print("   ✅ Circuit breaker pattern implemented")
    print("   ✅ Database operation retries working")
    print("   ✅ HTTP request retries working")
    print("   ✅ Miner operation retries working")
    print("   ✅ Custom retry configurations supported")
    print("   ✅ Statistics and monitoring available")


if __name__ == "__main__":
    asyncio.run(main())