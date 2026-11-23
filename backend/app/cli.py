"""Commandes d'administration.

Creer un agent support (l'inscription publique ne cree que des comptes 'user') :

    python -m app.cli create-agent --email agent@energydesk.local --full-name "Agent Demo"

Le mot de passe est lu dans la variable AGENT_PASSWORD, ou demande au clavier.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, User


def create_agent(email: str, full_name: str, password: str) -> str:
    email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=full_name, password_hash=hash_password(password))
            db.add(user)
            action = "cree"
        else:
            user.password_hash = hash_password(password)
            action = "mis a jour"
        user.role = Role.AGENT
        user.is_active = True
        db.commit()
        return f"Agent {action} : {email}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    agent = sub.add_parser("create-agent", help="Cree ou met a jour un compte agent support")
    agent.add_argument("--email", required=True)
    agent.add_argument("--full-name", required=True)
    args = parser.parse_args(argv)

    if args.command == "create-agent":
        password = os.environ.get("AGENT_PASSWORD") or getpass.getpass("Mot de passe de l'agent : ")
        if len(password) < 12:
            print("Mot de passe trop court (12 caracteres minimum).", file=sys.stderr)
            return 1
        print(create_agent(args.email, args.full_name, password))
    return 0


if __name__ == "__main__":
    sys.exit(main())
