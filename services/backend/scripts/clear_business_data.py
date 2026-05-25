from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, inspect, text
from sqlalchemy.engine import Engine, make_url

from recruit_station.core.settings import AppSettings, load_settings
from recruit_station.db.base import Base
from recruit_station.db.session import create_engine_from_settings, initialize_database


PRESERVED_TABLES = {
    "agent_definitions",
    "app_settings",
    "mcp_servers",
    "mcp_tools",
    "playbooks",
    "playbook_patches",
    "playbook_versions",
    "recruitment_state_machine_versions",
    "schema_migrations",
}


def _database_path(database_url: str) -> str:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        return database_url
    return str(Path(url.database).expanduser().resolve())


def _table_counts(engine: Engine, table_names: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table_name in sorted(table_names):
            counts[table_name] = int(connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0)
    return counts


def clear_business_data(settings: AppSettings, *, dry_run: bool = False, vacuum: bool = False) -> dict[str, Any]:
    engine = create_engine_from_settings(settings)
    initialize_database(engine)

    existing_tables = set(inspect(engine).get_table_names())
    modeled_tables = [table for table in reversed(Base.metadata.sorted_tables) if table.name in existing_tables]
    cleared_tables = [table.name for table in modeled_tables if table.name not in PRESERVED_TABLES]
    before = _table_counts(engine, set(cleared_tables) | (PRESERVED_TABLES & existing_tables))

    if not dry_run:
        with engine.begin() as connection:
            for table in modeled_tables:
                if table.name in PRESERVED_TABLES:
                    continue
                connection.execute(delete(table))
        if vacuum and make_url(settings.resolved_database_url()).drivername.startswith("sqlite"):
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text("VACUUM"))

    after = _table_counts(engine, set(cleared_tables) | (PRESERVED_TABLES & existing_tables))
    deleted = {name: before.get(name, 0) - after.get(name, 0) for name in cleared_tables}
    row_delta_key = "would_delete_rows" if dry_run else "deleted_rows"
    return {
        "database": _database_path(settings.resolved_database_url()),
        "dry_run": dry_run,
        "vacuum": vacuum and not dry_run,
        "preserved_tables": sorted(PRESERVED_TABLES & existing_tables),
        "cleared_tables": cleared_tables,
        row_delta_key: {name: count for name, count in (before if dry_run else deleted).items() if name in cleared_tables and count},
        "remaining_rows": {name: count for name, count in after.items() if count},
    }


def _known_local_settings(base_settings: AppSettings) -> list[AppSettings]:
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        base_settings,
        base_settings.with_overrides(
            data_dir=str(repo_root / "data"),
            database_url=f"sqlite:///{repo_root / 'data' / 'recruit-station.db'}",
        ),
        base_settings.with_overrides(
            data_dir=str(repo_root / "services" / "backend" / "data"),
            database_url=f"sqlite:///{repo_root / 'services' / 'backend' / 'data' / 'recruit-station.db'}",
        ),
        base_settings.with_overrides(
            data_dir=str(repo_root / "services" / "backend"),
            database_url=f"sqlite:///{repo_root / 'services' / 'backend' / 'agent.db'}",
        ),
    ]

    seen: set[str] = set()
    unique: list[AppSettings] = []
    for settings in candidates:
        key = _database_path(settings.resolved_database_url())
        if key in seen:
            continue
        seen.add(key)
        unique.append(settings)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear local RecruitStation business/runtime data while preserving deployment config.")
    parser.add_argument("--database-url", help="Override RECRUIT_STATION_DATABASE_URL for this cleanup run.")
    parser.add_argument("--known-local", action="store_true", help="Also clear known local development DB files in this checkout.")
    parser.add_argument("--dry-run", action="store_true", help="Report rows that would be cleared without deleting them.")
    parser.add_argument("--vacuum", action="store_true", help="Run SQLite VACUUM after deleting rows.")
    parser.add_argument("--yes", action="store_true", help="Required for destructive cleanup unless --dry-run is used.")
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        raise SystemExit("Refusing to clear data without --yes. Use --dry-run to inspect first.")

    settings = load_settings()
    if args.database_url:
        settings = settings.with_overrides(database_url=args.database_url)

    targets = _known_local_settings(settings) if args.known_local else [settings]
    results = [
        clear_business_data(target, dry_run=args.dry_run, vacuum=args.vacuum)
        for target in targets
    ]
    print(json.dumps({"databases": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
