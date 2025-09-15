"""
Test for async query optimizer implementation.
"""

import asyncio
import os
import tempfile
import pytest
from src.backend.services.query_optimizer import QueryOptimizer, DatabaseConnectionPool, retry_with_exponential_backoff


@pytest.mark.asyncio
async def test_connection_pool_creation():
    """Test that connection pool can be created and connections work."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        pool = DatabaseConnectionPool(db_path, max_connections=2)
        
        # Test getting a connection
        async with pool.get_connection() as conn:
            # Test basic query
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("test_value",))
            await conn.commit()
            
            async with conn.execute("SELECT name FROM test WHERE id = 1") as cursor:
                result = await cursor.fetchone()
                assert result[0] == "test_value"
        
        # Test connection stats
        stats = pool.get_connection_stats()
        assert stats['total_created'] >= 1
        assert stats['max_connections'] == 2
        
        await pool.close_all()
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_query_optimizer_async():
    """Test that QueryOptimizer works with async connections."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        optimizer = QueryOptimizer(db_path, max_connections=2)
        await optimizer.initialize()
        
        # Create a test table using the connection pool
        async with optimizer.connection_pool.get_connection() as conn:
            await conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
            await conn.execute("INSERT INTO test_table (value) VALUES (?)", ("test_data",))
            await conn.commit()
        
        # Test query optimization
        results = await optimizer.optimize_sqlite_query(
            "SELECT value FROM test_table WHERE id = ?", (1,)
        )
        
        assert len(results) == 1
        assert results[0]['value'] == "test_data"
        
        # Test caching - second query should be cached
        results2 = await optimizer.optimize_sqlite_query(
            "SELECT value FROM test_table WHERE id = ?", (1,)
        )
        assert results2 == results
        
        # Test connection stats
        stats = optimizer.get_connection_stats()
        assert 'connection_pool' in stats
        assert 'query_cache' in stats
        
        await optimizer.close()
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    """Test retry logic with exponential backoff."""
    call_count = 0
    
    async def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Attempt {call_count} failed")
        return "success"
    
    result = await retry_with_exponential_backoff(
        failing_function, 
        max_retries=3, 
        base_delay=0.01  # Very short delay for testing
    )
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_connection_health_check():
    """Test connection health checking."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        pool = DatabaseConnectionPool(db_path, max_connections=2)
        
        # Start health monitoring
        await pool.start_health_monitoring()
        
        # Get a connection and test it
        async with pool.get_connection() as conn:
            # Connection should be healthy
            is_healthy = await pool._test_connection_safe(conn)
            assert is_healthy is True
        
        await pool.stop_health_monitoring()
        await pool.close_all()
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    # Run a simple test
    asyncio.run(test_connection_pool_creation())
    print("Basic connection pool test passed!")