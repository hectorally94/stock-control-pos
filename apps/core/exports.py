"""Shared PDF / Excel export helpers for list pages.

Usage in a list view, on the FILTERED queryset BEFORE pagination:

    export = export_list_response(
        request,
        title="Mouvements de Stock",
        headers=["Date", "Produit", "Type", "Quantité"],
        rows=([m.created_at, m.product.name, ...] for m in movements),
        filename="mouvements_stock",
    )
    if export:
        return export

The view keeps its normal rendering when no ?export= parameter is present.
PDF is served inline so it opens in the browser (viewable/printable);
Excel is served as a download.
"""
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone

# Hard cap so a huge table cannot exhaust memory on the server
EXPORT_MAX_ROWS = 5000


# Rôle : formate une quantité sans zéros inutiles (5.000 donne « 5 ») ; None ou vide donne une chaîne vide.
# Liens : appelée par apps/products/views.py, apps/locations/views.py et apps/stock/views_frontend.py.
def fmt_qty(value):
    """Format a quantity without trailing zeros: 5.000 -> '5', 2.5 -> '2.5'."""
    if value is None or value == '':
        return ''
    s = f"{float(value):.3f}".rstrip('0').rstrip('.')
    return s or '0'


# Rôle : si ?export=xlsx ou pdf est présent, génère le fichier (5000 lignes maximum), sinon renvoie None.
# Liens : appelée par les vues de liste : pos, stock, products, locations, transfers, customers, accounting.
# Déclenchée par templates/partials/export_buttons.html ; appelle _xlsx_response ou _pdf_response.
def export_list_response(request, title, headers, rows, filename):
    """Return an xlsx/pdf HttpResponse if ?export= is requested, else None."""
    fmt = request.GET.get('export')
    if fmt not in ('xlsx', 'pdf'):
        return None

    rows = list(rows)[:EXPORT_MAX_ROWS]
    now = timezone.localtime()
    subtitle = f"Généré le {now.strftime('%d/%m/%Y à %H:%M')} — {len(rows)} ligne{'s' if len(rows) > 1 else ''}"
    file_stem = f"{filename}_{now.strftime('%Y%m%d_%H%M')}"

    if fmt == 'xlsx':
        return _xlsx_response(title, subtitle, headers, rows, file_stem)
    return _pdf_response(title, subtitle, headers, rows, file_stem)


# Rôle : prépare une valeur : None devient vide, dates au format JJ/MM/AAAA, nombres et textes inchangés.
# Liens : usage local : _xlsx_response et _trunc.
def _cell(value):
    """Normalize a value for output (dates -> DD/MM/YYYY, keep numbers)."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        if hasattr(value, 'hour'):
            value = timezone.localtime(value) if timezone.is_aware(value) else value
            return value.strftime('%d/%m/%Y %H:%M')
        return value.strftime('%d/%m/%Y')
    return value


# Rôle : construit le classeur Excel (titre, en-têtes stylés, largeurs auto) et le renvoie en téléchargement.
# Liens : appelée par export_list_response ; utilise openpyxl et _cell.
def _xlsx_response(title, subtitle, headers, rows, file_stem):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] or 'Export'

    # Title + subtitle
    ws.append([title])
    ws['A1'].font = Font(bold=True, size=14)
    ws.append([subtitle])
    ws['A2'].font = Font(italic=True, size=9, color='777777')
    ws.append([])

    # Header row
    header_fill = PatternFill(start_color='1F2937', end_color='1F2937', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    ws.append(list(headers))
    header_row = ws.max_row
    for col in range(1, len(headers) + 1):
        c = ws.cell(row=header_row, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')

    for row in rows:
        ws.append([_cell(v) for v in row])

    # Column widths from content (capped)
    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        longest = max(
            [len(str(headers[col - 1]))] +
            [len(str(_cell(r[col - 1]))) for r in rows if col - 1 < len(r)] or [10]
        )
        ws.column_dimensions[letter].width = min(max(longest + 2, 10), 45)

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    buf = BytesIO()
    wb.save(buf)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{file_stem}.xlsx"'
    return response


# Rôle : construit un PDF A4 paysage et le renvoie en « inline » pour l'ouvrir dans le navigateur.
# Liens : appelée par export_list_response ; utilise reportlab et _trunc.
def _pdf_response(title, subtitle, headers, rows, file_stem):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
        title=title,
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(title, styles['Title']),
        Paragraph(subtitle, styles['Italic']),
        Spacer(1, 0.4 * cm),
    ]

    # Rôle : convertit une cellule en texte et la coupe à 60 caractères pour tenir dans le tableau.
    # Liens : usage local dans _pdf_response ; appelle _cell.
    def _trunc(v, limit=60):
        s = str(_cell(v))
        return s if len(s) <= limit else s[:limit - 1] + '…'

    data = [list(headers)] + [[_trunc(v) for v in row] for row in rows]

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#9CA3AF')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    # inline: opens in the browser tab for viewing/printing; user can save it
    response['Content-Disposition'] = f'inline; filename="{file_stem}.pdf"'
    return response
