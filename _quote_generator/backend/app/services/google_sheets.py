"""Google Sheets integration for product import."""
from decimal import Decimal, InvalidOperation
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models.product import BillingPeriod, ProductCategory
from app.models.user import User


def get_sheets_service(user: User):
    """Get Google Sheets API service for a user."""
    if not user.google_access_token:
        raise ValueError("User does not have Google credentials")

    credentials = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
    )

    return build("sheets", "v4", credentials=credentials)


def parse_category(value: str) -> ProductCategory:
    """Parse category string to ProductCategory enum."""
    value_lower = value.lower().strip()
    category_map = {
        "license": ProductCategory.LICENSE,
        "service": ProductCategory.SERVICE,
        "training": ProductCategory.TRAINING,
        "subscription": ProductCategory.SUBSCRIPTION,
    }
    return category_map.get(value_lower, ProductCategory.SERVICE)


def parse_billing_period(value: str) -> BillingPeriod:
    """Parse billing period string to BillingPeriod enum."""
    value_lower = value.lower().strip().replace(" ", "-").replace("_", "-")
    period_map = {
        "one-time": BillingPeriod.ONE_TIME,
        "onetime": BillingPeriod.ONE_TIME,
        "monthly": BillingPeriod.MONTHLY,
        "quarterly": BillingPeriod.QUARTERLY,
        "annual": BillingPeriod.ANNUAL,
        "yearly": BillingPeriod.ANNUAL,
    }
    return period_map.get(value_lower, BillingPeriod.ONE_TIME)


def parse_decimal(value: str) -> Decimal:
    """Parse string to Decimal, handling currency symbols."""
    if not value:
        return Decimal("0.00")

    # Remove common currency symbols and whitespace
    cleaned = value.strip().replace("$", "").replace("€", "").replace("£", "")
    cleaned = cleaned.replace(",", "")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")


def parse_bool(value: str) -> bool:
    """Parse string to boolean."""
    return value.lower().strip() in ("true", "yes", "1", "y")


def import_products_from_sheet(
    user: User,
    spreadsheet_id: str,
    sheet_name: str = "Products",
) -> list[dict]:
    """Import products from a Google Sheet.

    Expected columns (case-insensitive):
    - Name (required)
    - SKU
    - Description
    - Category (license, service, training, subscription)
    - Unit Price (required)
    - Currency (USD, EUR, GBP)
    - Is Recurring (true/false)
    - Billing Period (one-time, monthly, quarterly, annual)

    Args:
        user: User with Google credentials
        spreadsheet_id: Google Sheets spreadsheet ID
        sheet_name: Name of the sheet to import from

    Returns:
        List of product dictionaries ready for creation
    """
    service = get_sheets_service(user)

    try:
        # Read the sheet data
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:H")
            .execute()
        )
    except HttpError as e:
        if e.resp.status == 404:
            raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
        elif e.resp.status == 403:
            raise ValueError("Access denied. Make sure the sheet is shared with your Google account.")
        raise

    values = result.get("values", [])

    if not values:
        return []

    # First row is headers
    headers = [h.lower().strip() for h in values[0]]
    products = []

    # Map column names to indices
    column_map = {
        "name": None,
        "sku": None,
        "description": None,
        "category": None,
        "unit price": None,
        "price": None,
        "currency": None,
        "is recurring": None,
        "recurring": None,
        "billing period": None,
    }

    for idx, header in enumerate(headers):
        if header in column_map:
            column_map[header] = idx

    # Find required columns
    name_col = column_map.get("name")
    price_col = column_map.get("unit price") or column_map.get("price")

    if name_col is None:
        raise ValueError("Missing required column: Name")

    # Process data rows
    for row_num, row in enumerate(values[1:], start=2):
        # Extend row to match headers length
        row = row + [""] * (len(headers) - len(row))

        name = row[name_col].strip() if name_col < len(row) else ""
        if not name:
            continue  # Skip empty rows

        product = {
            "name": name,
            "sku": None,
            "description": None,
            "category": ProductCategory.SERVICE,
            "unit_price": Decimal("0.00"),
            "currency": "USD",
            "is_recurring": False,
            "billing_period": BillingPeriod.ONE_TIME,
        }

        # SKU
        sku_col = column_map.get("sku")
        if sku_col is not None and sku_col < len(row):
            product["sku"] = row[sku_col].strip() or None

        # Description
        desc_col = column_map.get("description")
        if desc_col is not None and desc_col < len(row):
            product["description"] = row[desc_col].strip() or None

        # Category
        cat_col = column_map.get("category")
        if cat_col is not None and cat_col < len(row):
            product["category"] = parse_category(row[cat_col])

        # Unit Price
        if price_col is not None and price_col < len(row):
            product["unit_price"] = parse_decimal(row[price_col])

        # Currency
        curr_col = column_map.get("currency")
        if curr_col is not None and curr_col < len(row):
            currency = row[curr_col].strip().upper()
            if currency in ("USD", "EUR", "GBP"):
                product["currency"] = currency

        # Is Recurring
        rec_col = column_map.get("is recurring") or column_map.get("recurring")
        if rec_col is not None and rec_col < len(row):
            product["is_recurring"] = parse_bool(row[rec_col])

        # Billing Period
        period_col = column_map.get("billing period")
        if period_col is not None and period_col < len(row):
            product["billing_period"] = parse_billing_period(row[period_col])

        products.append(product)

    return products


def get_sample_template() -> str:
    """Return CSV content for a sample product import template."""
    return """Name,SKU,Description,Category,Unit Price,Currency,Is Recurring,Billing Period
Enterprise License,ENT-001,Full enterprise software license,license,5000.00,USD,false,one-time
Basic Support,SUP-BASIC,Basic support package,service,500.00,USD,true,monthly
Premium Support,SUP-PREM,Premium 24/7 support,service,2000.00,USD,true,monthly
Admin Training,TRN-ADMIN,Administrator training course,training,1500.00,USD,false,one-time
Pro Subscription,SUB-PRO,Professional tier subscription,subscription,99.00,USD,true,monthly
"""
