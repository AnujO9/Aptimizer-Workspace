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
    "structural": "Structural Design Basis Report",
    "water": "Water & Sanitation Infrastructure Report",
    "fire": "Fire & Life Safety Compliance Report",
    "accessibility": "Accessibility Compliance Report",
    "engineering": "IS / NBC Engineering Summary",
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


def _mod_table(module, col_widths=None):
    rows = [["Parameter", "Value", "Unit", "IS / NBC clause"]]
    for o in module.get("outputs", []):
        cl = o.get("clause") or {}
        rows.append([o["label"], str(o["value"]), o.get("unit", ""),
                     f"{cl.get('code', '')} {cl.get('clause', '')}".strip()])
    return _table(rows, col_widths or [58 * mm, 30 * mm, 18 * mm, 60 * mm], align_right_from=1)


def _checks_table(module):
    rows = [["Check", "Actual", "Required", "Status", "Clause"]]
    for c in module.get("checks", []):
        cl = c.get("clause") or {}
        rows.append([c["label"], str(c["actual"]), str(c["required"]), c["status"].upper(),
                     f"{cl.get('code', '')} {cl.get('clause', '')}".strip()])
    return _table(rows, [54 * mm, 22 * mm, 26 * mm, 16 * mm, 48 * mm], align_right_from=1)


def build_pdf(report_type: str, project: dict, a: dict, eng: dict = None) -> bytes:
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

    if report_type in ("executive", "quantity", "cost", "boq", "compliance", "parking", "utilities",
                       "structural", "water", "fire", "accessibility", "engineering"):
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

    if eng and report_type == "structural":
        m = eng["modules"]
        el += [Paragraph("1. Structural Load Estimator — IS 875 Parts 1–3", ss["Sec"]), _mod_table(m["loads"]),
               Paragraph(f"<b>{m['loads']['recommendation']['label']}:</b> {m['loads']['recommendation']['value']}", ss["Sub"]),
               Paragraph("2. Seismic Design — IS 1893 (Part 1):2016", ss["Sec"]), _mod_table(m["seismic"])]
        for w in m["seismic"]["warnings"]:
            el += [Paragraph(f"<b>{w['severity'].upper()}:</b> {w['text']}", ss["Sub"])]
        el += [Paragraph("3. Foundation Advisor — IS 6403 / IS 1904", ss["Sec"]), _mod_table(m["foundation"]),
               Paragraph(f"<b>Recommended:</b> {m['foundation']['recommendation']['value']}", ss["Sub"]),
               Paragraph("4. Concrete Mix Design — IS 10262:2019", ss["Sec"]), _mod_table(m["mix"]),
               Paragraph("12. Column Grid", ss["Sec"]), _mod_table(m["grid"])]
        if m["loads"].get("per_tower"):
            el += [Paragraph("Per-tower load & wind summary", ss["Sec"]),
                   _table([["Tower", "Floors", "Height (m)", "Footprint (m²)", "Column load (kN)",
                            "Column size (mm)", "Wind force (kN)"]] +
                          [[t["name"], t["floors"], _n(t["height_m"]), _n(t["footprint_sqm"]),
                            _n(t["column_load_kn"]), t["column_size_mm"], _n(t["wind_force_kn"])]
                           for t in m["loads"]["per_tower"]],
                          col_widths=[28 * mm, 16 * mm, 22 * mm, 26 * mm, 28 * mm, 26 * mm, 26 * mm])]
        if m["seismic"].get("per_tower"):
            el += [Paragraph("Per-tower seismic summary — IS 1893 Cl. 7.6", ss["Sec"]),
                   _table([["Tower", "Height (m)", "Ta (s)", "Sa/g", "Ah", "W (kN)", "VB (kN)", "VB/W (%)"]] +
                          [[t["name"], _n(t["height_m"]), _n(t["period_s"]), _n(t["sa_g"]), t["ah"],
                            _n(t["seismic_weight_kn"]), _n(t["base_shear_kn"]), _n(t["base_shear_pct_w"])]
                           for t in m["seismic"]["per_tower"]],
                          col_widths=[26 * mm, 22 * mm, 18 * mm, 18 * mm, 20 * mm, 26 * mm, 26 * mm, 22 * mm])]

    if eng and report_type == "water":
        m = eng["modules"]
        el += [Paragraph("Water Infrastructure — IS 1172:1993 / NBC Part 9", ss["Sec"]), _mod_table(m["water"]),
               Paragraph(f"<b>{m['water']['recommendation']['label']}:</b> {m['water']['recommendation']['value']}", ss["Sub"]),
               Paragraph("Storm Water & Rainwater Harvesting — IS 3764 / NBC Part 9", ss["Sec"]),
               _mod_table(m["storm"]), _checks_table(m["storm"])]

    if eng and report_type == "fire":
        m = eng["modules"]["fire"]
        el += [Paragraph(f"Fire & Life Safety — {m['passed']}/{m['total']} checks passed ({m['score']}%)", ss["Sec"]),
               _checks_table(m), Paragraph("Per-floor checklist", ss["Sec"]),
               _table([["Floor", "Level (m)", "Travel OK", "Extinguishers", "Refuge required", "Status"]] +
                      [[r["floor"], _n(r["level_m"]), "yes" if r["travel_ok"] else "no", r["extinguishers"],
                        "yes" if r["refuge_required"] else "—", r["status"].upper()] for r in m["floor_rows"]],
                      col_widths=[18 * mm, 24 * mm, 24 * mm, 30 * mm, 34 * mm, 26 * mm])]

    if eng and report_type == "accessibility":
        m = eng["modules"]["accessibility"]
        el += [Paragraph(f"Accessibility — score {m['score']}% ({m['passed']}/{m['total']} clauses met)", ss["Sec"]),
               _checks_table(m),
               Paragraph("Parking accessibility and NBC parking checks", ss["Sec"]),
               _checks_table(eng["modules"]["parking_nbc"])]

    if eng and report_type == "engineering":
        s = eng["summary"]
        el += [Paragraph("IS / NBC Engineering Summary", ss["Sec"]), _kv([
            ("Design city", f"{eng['city_reference']['city']}, {eng['city_reference']['state']}"),
            ("Seismic zone (IS 1893 Table 3)", s["seismic_zone"]),
            ("Design base shear (kN)", _n(s["base_shear_kn"])),
            ("Recommended column size (mm)", s["column_size"]),
            ("Foundation type (IS 1904)", s["foundation"]),
            ("Concrete mix (IS 10262)", s["mix_ratio"]),
            ("Water demand (litre/day)", _n(s["water_demand_lpd"])),
            ("STP capacity (KLD)", _n(s["stp_kld"])),
            ("RWH annual yield (litre)", _n(s["rwh_annual_l"])),
            ("Fire safety score (%)", _n(s["fire_score"])),
            ("NBC parking score (%)", _n(s["parking_score"])),
            ("Accessibility score (%)", _n(s["accessibility_score"])),
            ("Green rating", s["green_rating"]),
        ])]
        if eng["warnings"]:
            el += [Paragraph("Code warnings", ss["Sec"])]
            el += [Paragraph(f"<b>[{w['severity'].upper()}] {w['module']}:</b> {w['text']}", ss["Sub"])
                   for w in eng["warnings"]]
        if eng["missing_inputs"]:
            el += [Paragraph("Missing inputs", ss["Sec"]),
                   Paragraph(", ".join(eng["missing_inputs"]), ss["Sub"])]

    if eng and report_type == "executive":
        s = eng["summary"]
        el += [Paragraph("IS / NBC Engineering Highlights", ss["Sec"]), _kv([
            ("Seismic zone", s["seismic_zone"]), ("Base shear (kN)", _n(s["base_shear_kn"])),
            ("Column size (mm)", s["column_size"]), ("Foundation", s["foundation"]),
            ("Water demand (litre/day)", _n(s["water_demand_lpd"])), ("STP (KLD)", _n(s["stp_kld"])),
            ("Fire safety score (%)", _n(s["fire_score"])),
            ("Accessibility score (%)", _n(s["accessibility_score"])),
            ("Green rating", s["green_rating"]),
        ])]

    if report_type == "executive":
        g = project.get("gis") or {}
        suit, build = g.get("suitability"), g.get("buildability")
        if suit:
            el += [Paragraph(f"Site Intelligence Scorecard — suitability {suit['score']}% ({suit['grade']})", ss["Sec"]),
                   _table([["Factor", "Score", "Weight", "Contribution"]] +
                          [[b["factor"], _n(b["score"]), f"{b['weight_pct']}%", _n(b["contribution"])]
                           for b in suit.get("breakdown", [])],
                          col_widths=[75 * mm, 26 * mm, 26 * mm, 33 * mm])]
        if build:
            el += [Paragraph(f"Buildability — {'buildable' if build['buildable'] else 'constrained'} "
                             f"({build['critical_count']} critical, {build['warning_count']} warning)", ss["Sec"]),
                   _table([["Severity", "Finding", "Detail"]] +
                          [[f["severity"].upper(), f["title"], f["detail"]] for f in build.get("flags", [])],
                          col_widths=[20 * mm, 45 * mm, 95 * mm], align_right_from=3)]
        if not suit and not build:
            el += [Paragraph("Site Intelligence", ss["Sec"]),
                   Paragraph("No GIS site analysis has been run for this project yet — run GIS Intelligence "
                             "to include the site suitability scorecard.", ss["Sub"])]


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
