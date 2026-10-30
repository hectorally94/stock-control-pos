"""
PDF Receipt Generator using ReportLab
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime


# Rôle : formate un montant sans décimales, avec espace pour les milliers et suffixe FB.
# Liens : utilisée seulement par generate_receipt_pdf dans ce fichier.
def format_currency(amount):
    """Format amount as FB currency with space as thousands separator"""
    try:
        return f"{float(amount):,.0f} FB".replace(',', ' ')
    except:
        return f"{amount} FB"


# Rôle : construit le reçu PDF d'une vente avec ReportLab et renvoie un BytesIO ; page A4 ou large de 8 cm
# (thermal), mais tableaux larges de 14 à 15 cm dans les deux cas, donc plus larges que la page de 8 cm.
# Liens : sale_receipt_pdf (apps/pos/views_frontend.py), receipt (api/v1/views/pos.py) ; lit StoreSetting.
def generate_receipt_pdf(sale, format='A4'):
    """
    Generate a PDF receipt for a sale.
    
    Args:
        sale: Sale object with related items
        format: 'A4' or 'thermal' (80mm width)
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Create PDF document
    if format == 'thermal':
        # 80mm thermal printer
        pagesize = (8*cm, 29.7*cm)  # 80mm width, variable height
    else:
        pagesize = A4
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    )
    
    # Header Section
    from apps.settings.models import StoreSetting
    store_name = StoreSetting.get_setting('store_name', 'Ma Boutique')
    store_phone = StoreSetting.get_setting('store_phone', '')
    store_address = StoreSetting.get_setting('store_address', '')
    
    elements.append(Paragraph(store_name, title_style))
    
    if store_address:
        elements.append(Paragraph(store_address, header_style))
    if store_phone:
        elements.append(Paragraph(f"Tél: {store_phone}", header_style))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Receipt Title
    elements.append(Paragraph("REÇU DE VENTE", section_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Sale Information
    info_data = [
        ['N° de Vente:', sale.sale_number],
        ['Date:', sale.created_at.strftime('%d/%m/%Y %H:%M')],
        ['Caissier:', sale.user.get_full_name() or sale.user.username],
        ['Client:', sale.customer.name if sale.customer else 'Client anonyme'],
    ]
    
    info_table = Table(info_data, colWidths=[4*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Items Table
    items_data = [['Produit', 'Qté', 'P.U.', 'Total']]
    
    for item in sale.items.all():
        items_data.append([
            item.product_name,
            f"{float(item.quantity):.0f}" if item.quantity % 1 == 0 else f"{float(item.quantity):.2f}",
            format_currency(item.unit_price),
            format_currency(item.total_price)
        ])
    
    items_table = Table(items_data, colWidths=[7*cm, 2*cm, 3*cm, 3*cm])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Totals Section
    totals_data = []
    
    if sale.discount_amount > 0:
        totals_data.append(['Sous-total:', format_currency(sale.subtotal)])
        totals_data.append(['Remise:', f"-{format_currency(sale.discount_amount)}"])
    
    if sale.tax_amount > 0:
        totals_data.append(['TVA:', format_currency(sale.tax_amount)])
    
    totals_data.append(['TOTAL:', format_currency(sale.total_amount)])
    totals_data.append(['Montant payé:', format_currency(sale.amount_paid)])
    
    if sale.payment_method != 'credit' and sale.change_amount > 0:
        totals_data.append(['Monnaie:', format_currency(sale.change_amount)])
    
    totals_data.append(['Mode de paiement:', sale.get_payment_method_display()])
    
    totals_table = Table(totals_data, colWidths=[10*cm, 5*cm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -2), (-1, -2), 14),
        ('TEXTCOLOR', (0, -2), (-1, -2), colors.HexColor('#1E40AF')),
        ('FONTSIZE', (0, 0), (-1, -3), 10),
        ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, -2), (-1, -2), 2, colors.black),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 1*cm))
    
    # Footer
    footer_text = StoreSetting.get_setting('receipt_footer', 'Merci pour votre achat!')
    elements.append(Paragraph(footer_text, header_style))
    
    # Generation timestamp
    timestamp = datetime.now().strftime('%d/%m/%Y à %H:%M')
    elements.append(Paragraph(f"<i>Document généré le {timestamp}</i>", header_style))
    
    # Build PDF
    doc.build(elements)
    
    # Reset buffer position
    buffer.seek(0)
    return buffer

