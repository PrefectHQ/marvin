import alembic.script
from marvin.infra.database import _alembic_cfg


def test_only_single_head_revision_in_migrations():
    config = _alembic_cfg()
    script = alembic.script.ScriptDirectory.from_config(config)

    # script.version_locations = [orm_config().versions_dir]

    # This will raise if there are multiple heads
    head = script.get_current_head()

    assert head is not None, "Head revision is missing"
