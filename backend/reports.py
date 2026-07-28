"""PDF and Excel report generation."""
import io
from datetime import datetime, timezone

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BRAND = colors.HexColor("#2563EB")
DARK = colors.HexColor("#0F172A")
LIGHT = colors.HexColor("#F1F5F9")

REPORT_TITLES = {
    "boq": "Bill of Quantities Report",
    "cost": "Cost Estimation Report",
    "quantity": "Quantity Estimation Report",
    "parking": "Parking Planning Report",
    "compliance": "Compliance Validation Report",
    "utilities": "Utility Planning Report",
    "executive": "Executive Summary",
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H", parent=ss["Heading1"], fontSize=18, textColor=DARK, spaceAfter=4))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#475569")))
    ss.add(ParagraphStyle("Sec", parent=ss["Heading2"], fontSize=12, textColor=BRAND, spaceBefore=12, spaceAfter=6))
    return ss


def _table(data, col_widths=None, align_right_from=1):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    t.setStyle(TableStyle(style))
    return t


def _kv(pairs):
    return _table([["Parameter", "Value"]] + [[k, str(v)] for k, v in pairs], col_widths=[100 * mm, 65 * mm])


def _n(v):
    if isinstance(v, (int, float)):
        return f"{v:,.2f}"
    return str(v)


def build_pdf(report_type: str, project: dict, a: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    ss = _styles()
    el = [
        Paragraph("APTIMIZER", ParagraphStyle("brand", fontSize=10, textColor=BRAND, spaceAfter=2)),
        Paragraph(REPORT_TITLES.get(report_type, "Project Report"), ss["H"]),
        Paragraph(f"Project: {project.get('name', '')} &nbsp;|&nbsp; Client: {project.get('client', '-')} "
                  f"&nbsp;|&nbsp; Location: {project.get('location', '-')} &nbsp;|&nbsp; "
                  f"Generated: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}", ss["Sub"]),
        Spacer(1, 8),
    ]
    areas, boq, cost = a["areas"], a["boq"], a["cost"]
    cur = cost["currency"]

    if report_type in ("executive", "quantity", "cost", "boq", "compliance", "parking", "utilities"):
        el += [Paragraph("Key Project Metrics", ss["Sec"]), _kv([
            ("Plot Area (m²)", _n(areas["plot_area_sqm"])),
            ("Plot Area (acres)", _n(areas["plot_area_acres"])),
            ("Total Units", areas["total_units"]),
            ("Built-up Area (m²)", _n(areas["builtup_area_sqm"])),
            ("FAR / FSI", f"{areas['far']} / {areas['fsi']}"),
            ("Ground Coverage (%)", _n(areas["ground_coverage_pct"])),
        ])]

    if report_type in ("boq", "executive"):
        el += [Paragraph("Material Summary", ss["Sec"]),
               _table([["Item", "Unit", "Quantity", f"Rate ({cur})", f"Amount ({cur})"]] +
                      [[m["label"], m["unit"], _n(m["quantity"]), _n(m["rate"]), _n(m["amount"])]
                       for m in boq["materials"]] +
                      [["Material Total", "", "", "", _n(boq["material_total"])]],
                      col_widths=[60 * mm, 18 * mm, 28 * mm, 28 * mm, 33 * mm])]
    if report_type == "boq":
        el += [Paragraph("Labour Summary", ss["Sec"]),
               _table([["Trade", "Unit", "Man-days", f"Wage ({cur})", f"Amount ({cur})"]] +
                      [[l["label"], l["unit"], _n(l["quantity"]), _n(l["rate"]), _n(l["amount"])]
                       for l in boq["labour"]] +
                      [["Labour Total", "", "", "", _n(boq["labour_total"])]],
                      col_widths=[60 * mm, 20 * mm, 26 * mm, 28 * mm, 33 * mm]),
               Paragraph("Equipment Summary", ss["Sec"]),
               _table([["Equipment", "Unit", "Days", f"Rate ({cur})", f"Amount ({cur})"]] +
                      [[e["label"], e["unit"], _n(e["quantity"]), _n(e["rate"]), _n(e["amount"])]
                       for e in boq["equipment"]] +
                      [["Equipment Total", "", "", "", _n(boq["equipment_total"])]],
                      col_widths=[60 * mm, 20 * mm, 26 * mm, 28 * mm, 33 * mm])]

    if report_type == "quantity":
        el += [Paragraph("Estimated Quantities", ss["Sec"]),
               _table([["Material", "Unit", "Ratio", "Basis", "Quantity"]] +
                      [[q["label"], q["unit"], _n(q["ratio"]), q["basis"], _n(q["quantity"])]
                       for q in a["quantities"]["items"]],
                      col_widths=[60 * mm, 20 * mm, 26 * mm, 25 * mm, 34 * mm])]

    if report_type in ("cost", "executive"):
        el += [Paragraph("Cost Summary", ss["Sec"]), _kv([
            (f"Material Cost ({cur})", _n(cost["material"])),
            (f"Labour Cost ({cur})", _n(cost["labour"])),
            (f"Equipment Cost ({cur})", _n(cost["equipment"])),
            (f"Total Construction Cost ({cur})", _n(cost["total"])),
            (f"Cost per Flat ({cur})", _n(cost["per_unit"])),
            (f"Cost per m² ({cur})", _n(cost["per_sqm"])),
        ])]

    if report_type in ("parking", "executive"):
        p = a["parking"]
        el += [Paragraph("Parking Summary", ss["Sec"]), _kv([
            ("Required Slots", p["required_slots"]), ("Provided Slots", p["provided_slots"]),
            ("Basement Slots", p["basement_slots"]), ("Ground Slots", p["ground_slots"]),
            ("Visitor (req/prov)", f"{p['visitor_required']} / {p['visitor_provided']}"),
            ("EV (req/prov)", f"{p['ev_required']} / {p['ev_provided']}"),
            ("Accessible (req/prov)", f"{p['accessible_required']} / {p['accessible_provided']}"),
            ("Deficit", p["deficit"]), ("Area per slot (m²)", _n(p["area_per_slot_actual"])),
            ("Ramp validation", "PASS" if p["ramp_pass"] else "FAIL"),
        ])]

    if report_type in ("utilities", "executive"):
        u = a["utilities"]
        el += [Paragraph("Utility Planning", ss["Sec"]), _kv([
            ("Population", u["persons"]), ("Water Demand (litres/day)", _n(u["water_demand_lpd"])),
            ("UG Tank (m³)", _n(u["ug_tank_cum"])), ("OH Tank (m³)", _n(u["oh_tank_cum"])),
            ("STP Capacity (KLD)", _n(u["stp_capacity_kld"])), ("WTP Capacity (KLD)", _n(u["wtp_capacity_kld"])),
            ("Rainwater Harvest (litres/yr)", _n(u["rwh_annual_litres"])),
            ("Electrical Room (m²)", _n(u["electrical_room_sqm"])), ("Pump Room (m²)", _n(u["pump_room_sqm"])),
        ])]

    if report_type in ("compliance", "executive"):
        c = a["compliance"]
        el += [Paragraph(f"Compliance — {c['passed']}/{c['total']} rules passed "
                         f"(score {c['score']}%)", ss["Sec"]),
               _table([["Code", "Rule", "Limit", "Actual", "Status"]] +
                      [[r["code"], r["label"],
                        f"{'max' if r['operator'] == 'max' else 'min'} {r['threshold']}{r['unit']}",
                        _n(r["actual"]), r["status"].upper()] for r in c["results"]],
                      col_widths=[22 * mm, 72 * mm, 32 * mm, 25 * mm, 20 * mm], align_right_from=2)]

    el += [Spacer(1, 10), Paragraph("Generated by Aptimizer — figures are estimates based on configurable "
                                    "thumb-rule ratios and project rule sets.", ss["Sub"])]
    doc.build(el)
    return buf.getvalue()


def build_boq_excel(project: dict, a: dict) -> bytes:
    wb = Workbook()
    boq, cur = a["boq"], a["cost"]["currency"]
    head = Font(bold=True, color="FFFFFF")

    def sheet(ws, title, headers, rows, total_label, total):
        ws.title = title
        ws.append(headers)
        for c in ws[1]:
            c.font = head
            c.alignment = Alignment(horizontal="center")
        for r in rows:
            ws.append(r)
        ws.append([total_label, "", "", "", total])
        ws[f"A{ws.max_row}"].font = Font(bold=True)
        ws[f"E{ws.max_row}"].font = Font(bold=True)
        for col, w in zip("ABCDE", [38, 12, 16, 16, 18]):
            ws.column_dimensions[col].width = w

    ws1 = wb.active
    sheet(ws1, "Materials", ["Item", "Unit", "Quantity", f"Rate ({cur})", f"Amount ({cur})"],
          [[m["label"], m["unit"], m["quantity"], m["rate"], m["amount"]] for m in boq["materials"]],
          "Material Total", boq["material_total"])
    sheet(wb.create_sheet(), "Labour", ["Trade", "Unit", "Man-days", f"Wage ({cur})", f"Amount ({cur})"],
          [[l["label"], l["unit"], l["quantity"], l["rate"], l["amount"]] for l in boq["labour"]],
          "Labour Total", boq["labour_total"])
    sheet(wb.create_sheet(), "Equipment", ["Equipment", "Unit", "Days", f"Rate ({cur})", f"Amount ({cur})"],
          [[e["label"], e["unit"], e["quantity"], e["rate"], e["amount"]] for e in boq["equipment"]],
          "Equipment Total", boq["equipment_total"])

    ws4 = wb.create_sheet("Summary")
    ws4.append(["Project", project.get("name", "")])
    for k, v in [("Plot Area (m2)", a["areas"]["plot_area_sqm"]),
                 ("Built-up Area (m2)", a["areas"]["builtup_area_sqm"]),
                 ("Total Units", a["areas"]["total_units"]),
                 ("FAR", a["areas"]["far"]), ("FSI", a["areas"]["fsi"]),
                 (f"Material ({cur})", boq["material_total"]), (f"Labour ({cur})", boq["labour_total"]),
                 (f"Equipment ({cur})", boq["equipment_total"]),
                 (f"Grand Total ({cur})", boq["grand_total"]),
                 (f"Cost per Flat ({cur})", boq["cost_per_unit"]),
                 (f"Cost per m2 ({cur})", boq["cost_per_sqm"])]:
        ws4.append([k, v])
    ws4.column_dimensions["A"].width = 30
    ws4.column_dimensions["B"].width = 22

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
