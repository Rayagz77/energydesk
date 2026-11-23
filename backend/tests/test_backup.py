import time

import boto3
from moto import mock_aws

from app.backup import download_latest, list_backups, upload
from app.services.storage import S3Storage


@mock_aws
def test_backup_upload_and_download_latest(tmp_path):
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="energydesk-backups")
    storage = S3Storage("energydesk-backups", None, "us-east-1", "test", "test")

    old = tmp_path / "energydesk-20261124-020000.dump"
    old.write_bytes(b"ancienne sauvegarde")
    upload(storage, old)
    time.sleep(1)  # LastModified a une precision d'une seconde
    new = tmp_path / "energydesk-20261125-020000.dump"
    new.write_bytes(b"sauvegarde recente")
    upload(storage, new)

    assert [o["Key"] for o in list_backups(storage)] == [
        "postgres/energydesk-20261124-020000.dump",
        "postgres/energydesk-20261125-020000.dump",
    ]
    destination = tmp_path / "restore" / "latest.dump"
    key = download_latest(storage, destination)
    assert key.endswith("20261125-020000.dump")
    assert destination.read_bytes() == b"sauvegarde recente"
