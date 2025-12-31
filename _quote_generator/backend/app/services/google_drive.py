"""Google Drive integration for uploading quotes."""
import io
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.models.user import User


def get_drive_service(user: User):
    """Get Google Drive API service for a user."""
    if not user.google_access_token:
        raise ValueError("User does not have Google credentials")

    credentials = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
    )

    return build("drive", "v3", credentials=credentials)


def create_folder_if_not_exists(
    user: User,
    folder_name: str = "Quote Generator",
    parent_id: Optional[str] = None,
) -> str:
    """Create a folder in Google Drive if it doesn't exist.

    Returns the folder ID.
    """
    service = get_drive_service(user)

    # Search for existing folder
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
    ).execute()

    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create the folder
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]

    folder = service.files().create(
        body=file_metadata,
        fields="id",
    ).execute()

    return folder["id"]


def upload_pdf_to_drive(
    user: User,
    pdf_content: bytes,
    filename: str,
    folder_id: Optional[str] = None,
) -> dict:
    """Upload a PDF file to Google Drive.

    Returns dict with file id and web view link.
    """
    service = get_drive_service(user)

    # If no folder specified, create/get default folder
    if not folder_id:
        folder_id = create_folder_if_not_exists(user)

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_content),
        mimetype="application/pdf",
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink, webContentLink",
    ).execute()

    return {
        "id": file["id"],
        "web_view_link": file.get("webViewLink"),
        "web_content_link": file.get("webContentLink"),
    }


def create_google_doc_from_html(
    user: User,
    html_content: str,
    filename: str,
    folder_id: Optional[str] = None,
) -> dict:
    """Create a Google Doc from HTML content.

    Returns dict with file id and web view link.
    """
    service = get_drive_service(user)

    # If no folder specified, create/get default folder
    if not folder_id:
        folder_id = create_folder_if_not_exists(user)

    file_metadata = {
        "name": filename,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(html_content.encode("utf-8")),
        mimetype="text/html",
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    return {
        "id": file["id"],
        "web_view_link": file.get("webViewLink"),
    }


def upload_quote_to_drive(
    user: User,
    pdf_content: bytes,
    html_content: str,
    quote_number: str,
    customer_name: str,
) -> dict:
    """Upload quote as both PDF and Google Doc to Drive.

    Creates a folder structure: Quote Generator/Quotes/{customer_name}/

    Returns dict with PDF and Doc file IDs and links.
    """
    service = get_drive_service(user)

    # Create folder hierarchy
    root_folder_id = create_folder_if_not_exists(user, "Quote Generator")
    quotes_folder_id = create_folder_if_not_exists(user, "Quotes", root_folder_id)
    customer_folder_id = create_folder_if_not_exists(user, customer_name, quotes_folder_id)

    filename = f"{quote_number}"

    # Upload PDF
    pdf_result = upload_pdf_to_drive(
        user=user,
        pdf_content=pdf_content,
        filename=f"{filename}.pdf",
        folder_id=customer_folder_id,
    )

    # Create Google Doc
    doc_result = create_google_doc_from_html(
        user=user,
        html_content=html_content,
        filename=filename,
        folder_id=customer_folder_id,
    )

    return {
        "pdf_file_id": pdf_result["id"],
        "pdf_web_link": pdf_result["web_view_link"],
        "doc_file_id": doc_result["id"],
        "doc_web_link": doc_result["web_view_link"],
        "folder_id": customer_folder_id,
    }
