"""Google Gmail integration for creating quote email drafts."""
import base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models.user import User


def get_gmail_service(user: User):
    """Get Gmail API service for a user."""
    if not user.google_access_token:
        raise ValueError("User does not have Google credentials")

    credentials = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
    )

    return build("gmail", "v1", credentials=credentials)


def create_quote_email_html(
    quote_number: str,
    customer_name: str,
    contact_name: Optional[str],
    total: str,
    currency: str,
    valid_until: Optional[str],
    sender_name: str,
) -> str:
    """Generate HTML email body for quote."""
    greeting = f"Dear {contact_name}" if contact_name else "Hello"
    expiry_text = f"<p>This quote is valid until <strong>{valid_until}</strong>.</p>" if valid_until else ""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .highlight {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .total {{
            font-size: 1.2em;
            color: #2563eb;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 0.9em;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="container">
        <p>{greeting},</p>

        <p>Thank you for your interest in our products and services. Please find attached the quote
        <strong>{quote_number}</strong> for {customer_name}.</p>

        <div class="highlight">
            <p class="total">Quote Total: <strong>{currency} {total}</strong></p>
        </div>

        {expiry_text}

        <p>Please review the attached PDF for complete details including:</p>
        <ul>
            <li>Itemized products and services</li>
            <li>Pricing and any applicable discounts</li>
            <li>Terms and conditions</li>
        </ul>

        <p>If you have any questions or would like to proceed, please don't hesitate to reach out.
        We're happy to discuss any aspects of this quote.</p>

        <p>Best regards,<br>
        <strong>{sender_name}</strong></p>

        <div class="footer">
            <p>This quote was generated using Quote Generator.
            Reply to this email to get in touch with us.</p>
        </div>
    </div>
</body>
</html>
"""


def create_quote_email_text(
    quote_number: str,
    customer_name: str,
    contact_name: Optional[str],
    total: str,
    currency: str,
    valid_until: Optional[str],
    sender_name: str,
) -> str:
    """Generate plain text email body for quote."""
    greeting = f"Dear {contact_name}" if contact_name else "Hello"
    expiry_text = f"\nThis quote is valid until {valid_until}.\n" if valid_until else ""

    return f"""{greeting},

Thank you for your interest in our products and services. Please find attached the quote {quote_number} for {customer_name}.

Quote Total: {currency} {total}
{expiry_text}
Please review the attached PDF for complete details including:
- Itemized products and services
- Pricing and any applicable discounts
- Terms and conditions

If you have any questions or would like to proceed, please don't hesitate to reach out. We're happy to discuss any aspects of this quote.

Best regards,
{sender_name}

---
This quote was generated using Quote Generator.
Reply to this email to get in touch with us.
"""


def create_draft_with_attachment(
    user: User,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    attachment_content: bytes,
    attachment_filename: str,
    attachment_mimetype: str = "application/pdf",
    cc_emails: Optional[list[str]] = None,
) -> dict:
    """Create a Gmail draft with an attachment.

    Returns dict with draft id and message.
    """
    service = get_gmail_service(user)

    # Create the email message
    message = MIMEMultipart("mixed")
    message["to"] = to_email
    message["subject"] = subject

    if cc_emails:
        message["cc"] = ", ".join(cc_emails)

    # Create alternative part for text and HTML
    msg_alternative = MIMEMultipart("alternative")

    # Add plain text version
    text_part = MIMEText(text_body, "plain")
    msg_alternative.attach(text_part)

    # Add HTML version
    html_part = MIMEText(html_body, "html")
    msg_alternative.attach(html_part)

    message.attach(msg_alternative)

    # Add attachment
    maintype, subtype = attachment_mimetype.split("/", 1)
    attachment = MIMEBase(maintype, subtype)
    attachment.set_payload(attachment_content)

    # Encode the attachment
    import email.encoders
    email.encoders.encode_base64(attachment)

    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=attachment_filename,
    )
    message.attach(attachment)

    # Encode the entire message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    # Create draft
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw_message}},
    ).execute()

    return {
        "draft_id": draft["id"],
        "message_id": draft["message"]["id"],
    }


def create_quote_draft(
    user: User,
    to_email: str,
    quote_number: str,
    customer_name: str,
    contact_name: Optional[str],
    total: str,
    currency: str,
    valid_until: Optional[str],
    pdf_content: bytes,
    cc_emails: Optional[list[str]] = None,
) -> dict:
    """Create a Gmail draft for a quote with PDF attachment.

    Returns dict with draft id and message id.
    """
    subject = f"Quote {quote_number} for {customer_name}"

    html_body = create_quote_email_html(
        quote_number=quote_number,
        customer_name=customer_name,
        contact_name=contact_name,
        total=total,
        currency=currency,
        valid_until=valid_until,
        sender_name=user.name or user.email,
    )

    text_body = create_quote_email_text(
        quote_number=quote_number,
        customer_name=customer_name,
        contact_name=contact_name,
        total=total,
        currency=currency,
        valid_until=valid_until,
        sender_name=user.name or user.email,
    )

    return create_draft_with_attachment(
        user=user,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachment_content=pdf_content,
        attachment_filename=f"{quote_number}.pdf",
        cc_emails=cc_emails,
    )
