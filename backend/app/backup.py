"""Envoi et recuperation des sauvegardes PostgreSQL dans le stockage objet (ISO 27001 A.8.13).

Utilise par la CronJob Kubernetes de sauvegarde et par le test de restauration :

    python -m app.backup upload /backup/energydesk-20261125-020000.dump
    python -m app.backup download-latest /restore/latest.dump
    python -m app.backup list

Variables : BACKUP_BUCKET (bucket cible), S3_ENDPOINT_URL, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY,
S3_CREATE_BUCKET (true avec MinIO).
"""

import argparse
import os
import sys
from pathlib import Path

from app.core.config import get_settings
from app.services.storage import S3Storage

PREFIX = "postgres/"


def _storage() -> S3Storage:
    s = get_settings()
    bucket = os.environ.get("BACKUP_BUCKET", "energydesk-backups")
    storage = S3Storage(bucket, s.s3_endpoint_url, s.s3_region, s.s3_access_key, s.s3_secret_key)
    if s.s3_create_bucket:
        storage.ensure_bucket()
    return storage


def list_backups(storage: S3Storage) -> list[dict]:
    response = storage.client.list_objects_v2(Bucket=storage.bucket, Prefix=PREFIX)
    return sorted(response.get("Contents", []), key=lambda o: o["LastModified"])


def upload(storage: S3Storage, path: Path) -> str:
    key = f"{PREFIX}{path.name}"
    storage.client.upload_file(str(path), storage.bucket, key)
    return key


def download_latest(storage: S3Storage, destination: Path) -> str:
    backups = list_backups(storage)
    if not backups:
        raise SystemExit("Aucune sauvegarde trouvee.")
    key = backups[-1]["Key"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    storage.client.download_file(storage.bucket, key, str(destination))
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.backup")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("upload")
    up.add_argument("path", type=Path)
    down = sub.add_parser("download-latest")
    down.add_argument("destination", type=Path)
    sub.add_parser("list")
    args = parser.parse_args(argv)

    storage = _storage()
    if args.command == "upload":
        key = upload(storage, args.path)
        print(f"Sauvegarde envoyee : s3://{storage.bucket}/{key} ({args.path.stat().st_size} octets)")
    elif args.command == "download-latest":
        key = download_latest(storage, args.destination)
        print(f"Sauvegarde recuperee : s3://{storage.bucket}/{key} -> {args.destination}")
    else:
        for obj in list_backups(storage):
            print(f"{obj['LastModified'].isoformat()}  {obj['Size']:>10}  {obj['Key']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
