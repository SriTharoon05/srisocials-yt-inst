from sqlalchemy import inspect, text
from sqlmodel import create_engine
from app import database


def test_prefixed_schema_does_not_modify_other_project_tables(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'shared.db'}")
    monkeypatch.setattr(database, "engine", engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE channel (id INTEGER PRIMARY KEY, unrelated_value TEXT)"))
        connection.execute(text("INSERT INTO channel VALUES (1, 'other project data')"))
    database.init_db()
    database.init_db()  # repeat migrations are safe
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == {
            "channel", "srisocials_channel", "srisocials_video",
            "srisocials_teamuser", "srisocials_oauthattempt", "srisocials_adminuser"}
        assert connection.execute(text("SELECT unrelated_value FROM channel WHERE id = 1")).scalar_one() == "other project data"
        assert [c["name"] for c in inspector.get_columns("channel")] == ["id", "unrelated_value"]
        targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("srisocials_video")}
        assert targets == {"srisocials_channel", "srisocials_teamuser"}
    engine.dispose()
