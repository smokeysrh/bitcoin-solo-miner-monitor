"""
Simple test for async query optimizer implementation.
"""

import asyncio
import os
import tempfile
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.services.query_optimizer import QueryOptimizer, DatabaseConnectionPool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connection_pool():
    """Test that connection pool can be created and connections work."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        logger.info(f"Testing connection pool with database: {db_path}")
        pool = DatabaseConnectionPool(db_path, max_connections=2)
        
        # Test getting a connection
        async with pool.get_connection() as conn:
            logger.info("Got connection from pool")
            # Test basic query
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("test_value",))
            await conn.commit()
            logger.info("Created test table and inserted data")
            
            async with conn.execute("SELECT name FROM test WHERE id = 1") as cursor:
                result = await cursor.fetchone()
                assert result[0] == "test_value"
                logger.info(f"Query result: {result[0]}")
        
        # Test connection stats
        stats = pool.get_connection_stats()
        logger.info(f"Connection stats: {stats}")
        assert stats['total_created'] >= 1
        assert stats['max_connections'] == 2
        
        await pool.close_all()
        logger.info("Connection pool test passed!")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_query_optimizer():
    """Test that QueryOptimizer works with async connections."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        logger.info(f"Testing query optimizer with database: {db_path}")
        optimizer = QueryOptimizer(db_path, max_connections=2)
        await optimizer.initialize()
        logger.info("Query optimizer initialized")
        
        # Create a test table using the connection pool
        async with optimizer.connection_pool.get_connection() as conn:
            await conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
            await conn.execute("INSERT INTO test_table (value) VALUES (?)", ("test_data",))
            await conn.commit()
            logger.info("Created test table")
        
        # Test query optimization
        results = await optimizer.optimize_sqlite_query(
            "SELECT value FROM test_table WHERE id = ?", (1,)
        )
        
        assert len(results) == 1
        assert results[0]['value'] == "test_data"
        logger.info(f"Query results: {results}")
        
        # Test caching - second query should be cached
        results2 = await optimizer.optimize_sqlite_query(
            "SELECT value FROM test_table WHERE id = ?", (1,)
        )
        assert results2 == results
        logger.info("Query caching works")
        
        # Test connection stats
        stats = optimizer.get_connection_stats()
        logger.info(f"Optimizer stats: {stats}")
        assert 'connection_pool' in stats
        assert 'query_cache' in stats
        
        await optimizer.close()
        logger.info("Query optimizer test passed!")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run all tests."""
    try:
        await test_connection_pool()
        await test_query_optimizer()
        logger.info("All tests passed!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())