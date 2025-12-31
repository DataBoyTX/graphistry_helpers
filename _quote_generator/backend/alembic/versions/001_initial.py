"""Initial database schema.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255)),
        sa.Column("google_id", sa.String(255), unique=True, index=True),
        sa.Column("role", sa.String(20), default="user"),
        sa.Column("google_access_token", sa.Text),
        sa.Column("google_refresh_token", sa.Text),
        sa.Column("google_token_expiry", sa.String(50)),
        sa.Column("picture_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False, index=True),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("email", sa.String(255), index=True),
        sa.Column("phone", sa.String(50)),
        sa.Column("address_line1", sa.String(255)),
        sa.Column("address_line2", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country", sa.String(100), default="US"),
        sa.Column("tax_id", sa.String(50)),
        sa.Column("is_international", sa.Boolean, default=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Products table
    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(50), unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(20), default="service"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("is_recurring", sa.Boolean, default=False),
        sa.Column("billing_period", sa.String(20), default="one-time"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Quotes table
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_number", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("discount_percent", sa.Numeric(5, 2), default=0.00),
        sa.Column("discount_amount", sa.Numeric(12, 2), default=0.00),
        sa.Column("tax_rate", sa.Numeric(5, 2), default=0.00),
        sa.Column("tax_amount", sa.Numeric(12, 2), default=0.00),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("template_type", sa.String(20), default="us"),
        sa.Column("terms_and_conditions", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("valid_until", sa.Date),
        sa.Column("requires_approval", sa.Boolean, default=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("drive_doc_id", sa.String(255)),
        sa.Column("drive_pdf_id", sa.String(255)),
        sa.Column("gmail_draft_id", sa.String(255)),
        sa.Column("sent_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Quote Line Items table
    op.create_table(
        "quote_line_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_id", sa.String(36), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id")),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), default=1.00),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("discount_percent", sa.Numeric(5, 2), default=0.00),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("sort_order", sa.Integer, default=0),
    )

    # Orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_number", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("quote_id", sa.String(36), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("accepted_at", sa.DateTime),
        sa.Column("accepted_by", sa.String(255)),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("discount_amount", sa.Numeric(12, 2), default=0.00),
        sa.Column("tax_amount", sa.Numeric(12, 2), default=0.00),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, default=0.00),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Approval Settings table
    op.create_table(
        "approval_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("threshold_amount", sa.Numeric(12, 2), default=10000.00),
        sa.Column("require_approval_international", sa.Boolean, default=True),
        sa.Column("default_us_tax_rate", sa.Numeric(5, 2), default=0.00),
        sa.Column("default_international_vat_rate", sa.Numeric(5, 2), default=0.00),
        sa.Column("default_us_terms", sa.String(5000)),
        sa.Column("default_international_terms", sa.String(5000)),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("approval_settings")
    op.drop_table("orders")
    op.drop_table("quote_line_items")
    op.drop_table("quotes")
    op.drop_table("products")
    op.drop_table("customers")
    op.drop_table("users")
