import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://prometheus:chirag123@localhost:5432/prometheus")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(text("SELECT customer_id, status FROM customer_twins"))
        rows = result.all()
        print(f"Total twins: {len(rows)}")
        statuses = {}
        for r in rows:
            statuses[r[1]] = statuses.get(r[1], 0) + 1
            if r[1] == "active":
                print(f"Found active twin status for customer: {r[0]}")
        print("Status breakdown:", statuses)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
