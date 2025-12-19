"""Bootstrap an initial admin user when the auth database is empty.

Usage:
    python backend/scripts/bootstrap_admin.py --username alice --password 'S3cureP@ss'
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.database import async_init_database, get_async_db_session
from app.services.auth_service import ensure_initial_admin, public_user


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--username", required=True, help="Username for the admin account.")
    parser.add_argument("--password", required=True, help="Password for the admin account (use a strong secret).")
    parser.add_argument(
        "--allow-nonlocal",
        action="store_true",
        help="Explicitly allow running in non-local environments (strix/production). Use only during first-time bootstrap.",
    )
    return parser.parse_args()


async def _bootstrap(username: str, password: str, *, allow_nonlocal: bool) -> int:
    settings = get_settings()
    if settings.cortex_env != "local" and not allow_nonlocal:
        sys.stderr.write(
            "Refusing to bootstrap admin in non-local environment without --allow-nonlocal.\n"
            "Set CORTEX_ENV and ensure you understand the security implications.\n"
        )
        return 2

    await async_init_database()

    async with get_async_db_session() as session:
        try:
            user = await ensure_initial_admin(session, username, password)
        except ValueError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1

    user_view = public_user(user)
    sys.stdout.write(
        f"Admin user created: {user_view['username']} (id={user_view['id']})\n"
    )
    if settings.cortex_env != "local":
        sys.stdout.write("Reminder: rotate tokens and distribute credentials securely.\n")
    return 0


def main() -> None:
    args = _parse_args()
    if len(args.password) < 10:
        sys.stderr.write("Password is very short; use a longer, stronger secret.\n")
    exit_code = asyncio.run(_bootstrap(args.username, args.password, allow_nonlocal=args.allow_nonlocal))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

