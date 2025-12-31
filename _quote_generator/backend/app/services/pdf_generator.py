"""PDF generation service using WeasyPrint."""
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from weasyprint import HTML, CSS

from app.models.quote import Quote, TemplateType


def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """Format amount as currency string."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def format_date(d: Optional[datetime]) -> str:
    """Format datetime as date string."""
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%B %d, %Y")
    return str(d)


def generate_quote_html(quote: Quote) -> str:
    """Generate HTML content for a quote."""
    # Get customer info
    customer = quote.customer
    customer_name = customer.company_name if customer else "Unknown Customer"
    customer_contact = customer.contact_name if customer else ""
    customer_email = customer.email if customer else ""
    customer_address = ""
    if customer:
        address_parts = [
            customer.address_line1,
            customer.address_line2,
            f"{customer.city}, {customer.state} {customer.postal_code}".strip(", "),
            customer.country,
        ]
        customer_address = "<br>".join(p for p in address_parts if p and p.strip())

    # Build line items table
    line_items_html = ""
    for item in quote.line_items:
        discount_str = f"{item.discount_percent}%" if item.discount_percent > 0 else "-"
        line_items_html += f"""
        <tr>
            <td class="description">{item.description}</td>
            <td class="number">{item.quantity}</td>
            <td class="number">{format_currency(item.unit_price, quote.currency)}</td>
            <td class="number">{discount_str}</td>
            <td class="number">{format_currency(item.line_total, quote.currency)}</td>
        </tr>
        """

    # Build totals section
    totals_html = f"""
    <tr>
        <td colspan="4" class="label">Subtotal</td>
        <td class="number">{format_currency(quote.subtotal, quote.currency)}</td>
    </tr>
    """

    if quote.discount_amount > 0:
        totals_html += f"""
        <tr>
            <td colspan="4" class="label">Discount ({quote.discount_percent}%)</td>
            <td class="number discount">-{format_currency(quote.discount_amount, quote.currency)}</td>
        </tr>
        """

    if quote.tax_amount > 0:
        tax_label = "Sales Tax" if quote.template_type == TemplateType.US else "VAT"
        totals_html += f"""
        <tr>
            <td colspan="4" class="label">{tax_label} ({quote.tax_rate}%)</td>
            <td class="number">{format_currency(quote.tax_amount, quote.currency)}</td>
        </tr>
        """

    totals_html += f"""
    <tr class="total-row">
        <td colspan="4" class="label"><strong>Total</strong></td>
        <td class="number"><strong>{format_currency(quote.total, quote.currency)}</strong></td>
    </tr>
    """

    # Notes section
    notes_html = ""
    if quote.notes:
        notes_html = f"""
        <div class="notes">
            <h3>Notes</h3>
            <p>{quote.notes.replace(chr(10), '<br>')}</p>
        </div>
        """

    # Terms section
    terms_html = ""
    if quote.terms_and_conditions:
        terms_html = f"""
        <div class="terms">
            <h3>Terms & Conditions</h3>
            <p>{quote.terms_and_conditions.replace(chr(10), '<br>')}</p>
        </div>
        """

    # International-specific content
    international_info = ""
    if quote.template_type == TemplateType.INTERNATIONAL and customer and customer.tax_id:
        international_info = f"""
        <div class="tax-info">
            <p><strong>VAT Number:</strong> {customer.tax_id}</p>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Quote {quote.quote_number}</title>
    </head>
    <body>
        <div class="header">
            <div class="company">
                <h1>Quote</h1>
                <p class="quote-number">{quote.quote_number}</p>
            </div>
            <div class="quote-info">
                <table>
                    <tr>
                        <td class="label">Date:</td>
                        <td>{format_date(quote.created_at)}</td>
                    </tr>
                    <tr>
                        <td class="label">Valid Until:</td>
                        <td>{format_date(quote.valid_until)}</td>
                    </tr>
                    <tr>
                        <td class="label">Currency:</td>
                        <td>{quote.currency}</td>
                    </tr>
                </table>
            </div>
        </div>

        <div class="customer-section">
            <h3>Bill To:</h3>
            <div class="customer-info">
                <p><strong>{customer_name}</strong></p>
                {f'<p>{customer_contact}</p>' if customer_contact else ''}
                {f'<p>{customer_email}</p>' if customer_email else ''}
                {f'<p>{customer_address}</p>' if customer_address else ''}
            </div>
            {international_info}
        </div>

        <div class="line-items">
            <table>
                <thead>
                    <tr>
                        <th class="description">Description</th>
                        <th class="number">Qty</th>
                        <th class="number">Unit Price</th>
                        <th class="number">Discount</th>
                        <th class="number">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {line_items_html}
                </tbody>
            </table>
        </div>

        <div class="totals">
            <table>
                <tbody>
                    {totals_html}
                </tbody>
            </table>
        </div>

        {notes_html}
        {terms_html}

        <div class="footer">
            <p>Thank you for your business!</p>
        </div>
    </body>
    </html>
    """

    return html


def get_quote_css() -> str:
    """Get CSS styles for the quote PDF."""
    return """
    @page {
        size: letter;
        margin: 1in;
    }

    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.4;
        color: #333;
    }

    .header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 30px;
        padding-bottom: 20px;
        border-bottom: 2px solid #2563eb;
    }

    .header h1 {
        font-size: 28pt;
        color: #2563eb;
        margin: 0;
    }

    .quote-number {
        font-size: 14pt;
        color: #666;
        margin-top: 5px;
    }

    .quote-info table {
        text-align: right;
    }

    .quote-info td {
        padding: 3px 0;
    }

    .quote-info .label {
        font-weight: bold;
        padding-right: 10px;
        color: #666;
    }

    .customer-section {
        margin-bottom: 30px;
    }

    .customer-section h3 {
        font-size: 10pt;
        color: #666;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .customer-info p {
        margin: 3px 0;
    }

    .tax-info {
        margin-top: 10px;
        padding: 10px;
        background: #f8fafc;
        border-radius: 4px;
    }

    .line-items {
        margin-bottom: 20px;
    }

    .line-items table {
        width: 100%;
        border-collapse: collapse;
    }

    .line-items th {
        background: #f1f5f9;
        padding: 12px 10px;
        text-align: left;
        font-weight: 600;
        font-size: 9pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 2px solid #e2e8f0;
    }

    .line-items td {
        padding: 12px 10px;
        border-bottom: 1px solid #e2e8f0;
    }

    .line-items .description {
        width: 40%;
    }

    .line-items .number {
        text-align: right;
        width: 15%;
    }

    .line-items th.number {
        text-align: right;
    }

    .totals {
        margin-left: auto;
        width: 300px;
    }

    .totals table {
        width: 100%;
    }

    .totals td {
        padding: 8px 10px;
    }

    .totals .label {
        text-align: right;
        padding-right: 20px;
        color: #666;
    }

    .totals .number {
        text-align: right;
        width: 100px;
    }

    .totals .discount {
        color: #dc2626;
    }

    .totals .total-row {
        border-top: 2px solid #333;
        font-size: 12pt;
    }

    .totals .total-row td {
        padding-top: 12px;
    }

    .notes, .terms {
        margin-top: 30px;
        padding: 15px;
        background: #f8fafc;
        border-radius: 4px;
    }

    .notes h3, .terms h3 {
        font-size: 10pt;
        color: #666;
        margin: 0 0 10px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .notes p, .terms p {
        margin: 0;
        font-size: 9pt;
        color: #555;
    }

    .footer {
        margin-top: 40px;
        text-align: center;
        color: #666;
        font-size: 9pt;
    }
    """


def generate_quote_pdf(quote: Quote) -> bytes:
    """Generate a PDF for a quote.

    Args:
        quote: The quote object with relationships loaded

    Returns:
        PDF content as bytes
    """
    html_content = generate_quote_html(quote)
    css = CSS(string=get_quote_css())

    # Generate PDF
    html = HTML(string=html_content)
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer, stylesheets=[css])

    return pdf_buffer.getvalue()
