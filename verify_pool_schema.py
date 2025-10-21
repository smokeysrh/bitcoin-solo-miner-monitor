#!/usr/bin/env python3
"""Quick script to verify network_health table schema."""

import asyncio
import aiosqlite
from config.app_config import DB_CONFIG


async def main():
    conn = await aiosqlite.connect(DB_CONFIG['sqlite']['path'])
    
    # Get table structure
    cursor = await conn.execute('PRAGMA table_info(network_health)')
    cols = await cursor.fetchall()
    
    print('\nnetwork_health table columns:')
    print('-' * 50)
    for col in cols:
        print(f'  {col[1]:30} {col[2]:10}')
    
    # Get indexes
    cursor = await conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='network_health'
    """)
    indexes = await cursor.fetchall()
    
    print('\nIndexes:')
    print('-' * 50)
    for idx in indexes:
        print(f'  {idx[0]}')
    
    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
