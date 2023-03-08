import asyncio

import marvin
import marvin.examples.prefect


async def main():
    # reset the DB
    await marvin.database.ddl.reset_db(confirm=True)

    # hydrate with docs
    await marvin.examples.prefect.load_prefect()


if __name__ == "__main__":
    asyncio.run(main())
