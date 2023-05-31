import marvin
import pytest
import sqlmodel


@pytest.fixture(scope="session")
def session_tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp("marvin")


@pytest.fixture(scope="session", autouse=True)
async def test_database(session_tmp_path):
    """Set up the test database"""
    marvin.infra.database.alembic_upgrade()
    yield
    marvin.infra.database.alembic_downgrade()


@pytest.fixture(autouse=True)
async def clear_test_database(test_database, session):
    """Clear the test database"""
    yield

    for table in reversed(sqlmodel.SQLModel.metadata.sorted_tables):
        await session.execute(table.delete())

    await session.commit()


@pytest.fixture
async def session():
    async with marvin.infra.database.session_context() as session:
        yield session
