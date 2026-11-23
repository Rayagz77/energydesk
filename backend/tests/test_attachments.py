import hashlib

import boto3
from moto import mock_aws

from app.services.files import detect_content_type, sanitize_filename
from app.services.storage import S3Storage
from tests.conftest import create_ticket

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


def upload(client, ticket_id, headers, data, name="photo.png", declared="image/png"):
    return client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": (name, data, declared)},
        headers=headers,
    )


def test_upload_and_download(client, user_headers, storage):
    ticket = create_ticket(client, user_headers)
    response = upload(client, ticket["id"], user_headers, PNG)
    assert response.status_code == 201, response.text
    attachment = response.json()
    assert attachment["content_type"] == "image/png"
    assert attachment["size_bytes"] == len(PNG)

    # Le fichier est dans le stockage objet, sous une cle qui ne contient pas le nom d'origine.
    [key] = storage.objects.keys()
    assert key.startswith(f"tickets/{ticket['id']}/")
    assert "photo" not in key

    download = client.get(f"/api/v1/attachments/{attachment['id']}/download", headers=user_headers)
    assert download.status_code == 200
    assert download.content == PNG
    assert download.headers["x-content-type-options"] == "nosniff"


def test_type_is_detected_from_content_not_from_name(client, user_headers):
    ticket = create_ticket(client, user_headers)
    fake_png = b"MZ\x90\x00" + b"\x00" * 64  # en-tete d'un executable Windows
    response = upload(client, ticket["id"], user_headers, fake_png, name="photo.png")
    assert response.status_code == 415


def test_pdf_is_accepted_even_with_wrong_declared_type(client, user_headers):
    ticket = create_ticket(client, user_headers)
    response = upload(client, ticket["id"], user_headers, PDF, name="rapport.pdf", declared="text/plain")
    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"


def test_too_large_file_is_rejected(client, user_headers):
    ticket = create_ticket(client, user_headers)
    big = PNG + b"\x00" * (5 * 1024 * 1024)
    response = upload(client, ticket["id"], user_headers, big)
    assert response.status_code == 413


def test_other_user_cannot_upload_or_download(client, user_headers, other_headers):
    ticket = create_ticket(client, user_headers)
    attachment = upload(client, ticket["id"], user_headers, PNG).json()
    assert upload(client, ticket["id"], other_headers, PNG).status_code == 404
    download = client.get(f"/api/v1/attachments/{attachment['id']}/download", headers=other_headers)
    assert download.status_code == 404


def test_agent_can_download(client, user_headers, agent_headers):
    ticket = create_ticket(client, user_headers)
    attachment = upload(client, ticket["id"], user_headers, PNG).json()
    download = client.get(f"/api/v1/attachments/{attachment['id']}/download", headers=agent_headers)
    assert download.status_code == 200


def test_attachment_listed_in_ticket_detail(client, user_headers):
    ticket = create_ticket(client, user_headers)
    upload(client, ticket["id"], user_headers, PNG, name="../../etc/passwd.png")
    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=user_headers).json()
    assert [a["original_filename"] for a in detail["attachments"]] == ["passwd.png"]


def test_helpers():
    assert detect_content_type(PNG) == "image/png"
    assert detect_content_type(b"\xff\xd8\xff\xe0data") == "image/jpeg"
    assert detect_content_type(b"<script>") is None
    assert sanitize_filename("C:\\Users\\x\\Relevé été.pdf") == "Releve ete.pdf"
    assert sanitize_filename("") == "fichier"


@mock_aws
def test_ensure_bucket_creates_missing_bucket_in_any_region():
    storage = S3Storage("energydesk-paris", None, "eu-west-3", "test", "test")
    storage.ensure_bucket()
    storage.ensure_bucket()  # deuxieme appel : le bucket existe deja, pas d'erreur
    assert storage.ping() is True


@mock_aws
def test_s3_storage_roundtrip():
    """Le client S3 reel (boto3) fonctionne contre un faux S3 (moto)."""
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="energydesk-test")
    storage = S3Storage("energydesk-test", None, "us-east-1", "test", "test")
    storage.put_object("tickets/x/1", PDF, "application/pdf")
    data = b"".join(storage.iter_object("tickets/x/1"))
    assert hashlib.sha256(data).hexdigest() == hashlib.sha256(PDF).hexdigest()
    assert storage.ping() is True
