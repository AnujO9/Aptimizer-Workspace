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

# Eleven reports, one per thing a reader actually asks for. Five were merged rather than
# kept: they repeated numbers the survivor already carried, and a reader choosing between
# two reports with the same figures picks wrong half the time.
#
#   utilities      -> water        (identical STP, tank and RWH sizing)
#   quantity       -> boq          (quantities are the unpriced half of the bill)
#   accessibility  -> compliance   (it is a compliance chapter, not a document)
#   controls       -> compliance   (setbacks are checked, not designed, at this stage)
#   parking        -> executive    (a client reads slots, not a parking document)
REPORT_TITLES = {
    "executive": "Executive Summary",
    "site": "Site Analysis Report",
    "compliance": "Compliance Validation Report",
    "engineering": "IS / NBC Engineering Summary",
    "structural": "Structural Design Basis Report",
    "water": "Water & Sanitation Infrastructure Report",
    "fire": "Fire & Life Safety Compliance Report",
    "sustainability": "Sustainability & Carbon Report",
    "boq": "BOQ & Quantities Report",
    "cost": "Cost & Feasibility Report",
    "programme": "Construction Programme Report",
}

# Merged ids still resolve, so an old link or a saved bookmark lands on the report that
# now carries those numbers instead of a 400.
MERGED_INTO = {
    "utilities": "water",
    "quantity": "boq",
    "accessibility": "compliance",
    "controls": "compliance",
    "parking": "executive",
}

# The order a merged PDF reads in: site, then design, then verification, then commercial.
ALL_ORDER = ["executive", "site", "compliance", "engineering", "structural", "water",
             "fire", "sustainability", "boq", "cost", "programme"]


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


def _programme(project: dict, a: dict):
    """The programme, or None. Imported here so reports never hard-depend on it."""
    try:
        import schedule as schedlib
        plan = schedlib.plan_schedule(project, a, (project.get("schedule") or {}))
        return plan if plan.get("ok") else None
    except Exception:
        return None


def _finance(project: dict, a: dict):
    try:
        import finance as financelib
        return financelib.analyse(project, a, project.get("finance"))
    except Exception:
        return None


def _optimisers(project: dict, a: dict, eng: dict):
    out = {}
    try:
        import optimise as optlib
        out.update({k: v for k, v in optlib.analyse(project, a, eng).items()
                    if isinstance(v, dict) and "current" in v})
    except Exception:
        pass
    try:
        import planopt as planoptlib
        out.update({k: v for k, v in planoptlib.analyse(project, a).items()
                    if isinstance(v, dict) and "current" in v})
    except Exception:
        pass
    return out


def build_pdf(report_type: str, project: dict, a: dict, eng: dict = None) -> bytes:
    report_type = MERGED_INTO.get(report_type, report_type)
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

    if report_type in REPORT_TITLES:
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

    if report_type == "boq":
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

    if eng and report_type == "compliance":
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
            # m13 and m14. The summary claims to cover the engineering modules, so leaving
            # carbon and plantation out of it would make it quietly wrong.
            ("Embodied carbon (tCO2e)", _n(s.get("embodied_carbon_tco2e"))),
            ("Embodied carbon (kgCO2e/m2)", _n(s.get("carbon_per_sqm_kg"))),
            ("Trees required", _n(s.get("trees_required"))),
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


    # ---------------------------------------------------------------- programme
    if report_type == "programme":
        plan = _programme(project, a)
        if not plan:
            el += [Paragraph("Construction Programme", ss["Sec"]),
                   Paragraph("The programme could not be generated for this project. Check "
                             "that towers, floors and quantities are set.", ss["Sub"])]
        else:
            saf = plan.get("safety") or {}
            el += [Paragraph("Programme Summary", ss["Sec"]), _kv([
                ("Start", plan["start"]), ("Completion", plan["finish"]),
                ("Duration (months)", _n(plan["duration_months"])),
                ("Calendar days", _n(plan["duration_calendar_days"])),
                ("Tasks", _n(plan.get("activity_count"))),
                ("Floor cycle (days)", _n(saf.get("floor_cycle_days"))),
            ])]
            el += [Paragraph("Phase Breakdown", ss["Sec"]),
                   _table([["Phase", "Start", "Finish", "Days", "Tasks", f"Cost ({cur})"]] +
                          [[ph["phase"], ph["start"], ph["finish"], _n(ph["calendar_days"]),
                            _n(ph["activities"]), _n(ph["cost"])] for ph in plan["phases"]],
                          col_widths=[42 * mm, 26 * mm, 26 * mm, 18 * mm, 18 * mm, 34 * mm])]
            crit = [x for x in plan.get("activities", []) if x.get("critical")][:20]
            if crit:
                el += [Paragraph("Critical Path (first 20 tasks)", ss["Sec"]),
                       _table([["Task", "Start", "Finish", "Days"]] +
                              [[x["name"], x["start"], x["finish"], _n(x["work_days"])]
                               for x in crit],
                              col_widths=[86 * mm, 26 * mm, 26 * mm, 26 * mm])]
            if saf:
                el += [Paragraph("Safety Basis (IS 456)", ss["Sec"]),
                       Paragraph(f"The floor cycle cannot be compressed below "
                                 f"{saf.get('prop_removal_days')} calendar days — "
                                 f"{saf.get('governing_rule')}. Adding labour shortens every "
                                 "other activity, never this one.", ss["Sub"])]
            findings = (saf.get("findings") or [])
            if findings:
                el += [Paragraph("Safety Findings", ss["Sec"])] + \
                      [Paragraph(f"<b>[{f['severity'].upper()}]</b> {f['text']}", ss["Sub"])
                       for f in findings]

    # ---------------------------------------------------------------- feasibility
    if report_type == "cost":
        fin = _finance(project, a)
        if fin:
            el += [Paragraph("Feasibility & Return", ss["Sec"]), _kv([
                ("Gross revenue", _n(fin["revenue"]["gross"])),
                ("Total project cost", _n(fin["cost"]["total"])),
                ("Net profit", _n(fin["profit"]["net"])),
                ("Margin (%)", _n(fin["profit"]["margin_pct"])),
                ("Return on cost (%)", _n(fin["profit"]["roi_pct"])),
                ("Annual IRR (%)", _n(fin["profit"]["irr_pct"])
                 if fin["profit"]["irr_pct"] is not None else "not reachable"),
                ("Cash positive (month)", fin["timing"]["payback_month"]
                 if fin["timing"]["payback_month"] is not None else "never"),
                ("Peak funding needed", _n(fin["timing"]["peak_funding_need"])),
                ("Break-even sale rate (per sqft)", _n(fin["break_even"]["sale_rate_per_sqft"])),
                ("Break-even flats", _n(fin["break_even"]["units"])),
            ])]
            el += [Paragraph("Revenue by Flat Type", ss["Sec"]),
                   _table([["Type", "Flats", "Saleable (sqft)", f"Rate ({cur})", f"Revenue ({cur})"]] +
                          [[r["type"].upper(), _n(r["units"]), _n(r["saleable_sqft"]),
                            _n(r["rate_per_sqft"]), _n(r["revenue"])]
                           for r in fin["revenue"]["by_type"]],
                          col_widths=[36 * mm, 22 * mm, 38 * mm, 30 * mm, 41 * mm])]
            flow = fin.get("cash_flow") or []
            if flow:
                every3 = [f for i, f in enumerate(flow) if i % 3 == 0]
                el += [Paragraph("Cash Flow (every third month)", ss["Sec"]),
                       _table([["Month", f"Out ({cur})", f"In ({cur})", f"Cumulative ({cur})"]] +
                              [[f["month"], _n(f["outflow"]), _n(f["inflow"]), _n(f["cumulative"])]
                               for f in every3],
                              col_widths=[24 * mm, 46 * mm, 46 * mm, 51 * mm])]

    if report_type == "cost":
        opt = _optimisers(project, a, eng)
        if opt:
            rows = []
            for key, o in opt.items():
                cur, best = o["current"], o["best"]
                unit = cur.get("unit") or ""
                change = "; ".join(
                    f'{c["lever"]}: {c["from"]} -> {c["to"]}'
                    for c in (o.get("changes") or [])[:2]) or "no change available"
                rows.append([o["title"],
                             f'{_n(cur["value"])} {unit}'.strip(),
                             f'{_n(best["value"])} {unit}'.strip(),
                             change])
            el += [Paragraph("Optimisation Findings", ss["Sec"]),
                   Paragraph("Each row is what the scheme does today, the best the search "
                             "found, and the change that gets there. Nothing here has been "
                             "applied.", ss["Sub"]),
                   _table([["Optimiser", "Now", "Best found", "Change required"]] + rows,
                          col_widths=[34 * mm, 28 * mm, 28 * mm, 77 * mm],
                          align_right_from=4)]

    # ---------------------------------------------------------------- site
    if report_type == "site":
        g = project.get("gis") or {}
        if not g:
            el += [Paragraph("Site Analysis", ss["Sec"]),
                   Paragraph("No site analysis has been run. Open GIS Intelligence and run it "
                             "to populate this report.", ss["Sub"])]
        else:
            t, fl = g.get("terrain") or {}, g.get("flood") or {}
            el += [Paragraph("Terrain & Flood", ss["Sec"]), _kv([
                ("Average slope (%)", _n(t.get("avg_slope_pct"))),
                ("Slope class", t.get("slope_class", "-")),
                ("Relief (m)", _n(t.get("relief_m"))),
                ("Flood risk", fl.get("level", "-")),
                ("Flood score", _n(fl.get("score"))),
            ])]
            fac = (g.get("sun") or {}).get("facades") or []
            if fac:
                el += [Paragraph("Sun & Orientation", ss["Sec"]),
                       _table([["Facade", "Bearing", "Sun hours", "Guidance"]] +
                              [[f["facade"], f"{f['bearing_deg']}°", _n(f["sun_hours_equinox"]),
                                f["recommendation"]] for f in fac],
                              col_widths=[32 * mm, 20 * mm, 22 * mm, 90 * mm], align_right_from=4)]
            acc = g.get("accessibility") or {}
            if acc:
                el += [Paragraph("Access", ss["Sec"]),
                       Paragraph(str(acc.get("summary") or acc.get("grade") or "-"), ss["Sub"])]
            suit = g.get("suitability")
            if suit:
                el += [Paragraph(f"Suitability — {suit['score']}% ({suit['grade']})", ss["Sec"]),
                       _table([["Factor", "Score", "Weight", "Contribution"]] +
                              [[b["factor"], _n(b["score"]), f"{b['weight_pct']}%", _n(b["contribution"])]
                               for b in suit.get("breakdown", [])],
                              col_widths=[75 * mm, 26 * mm, 26 * mm, 33 * mm])]
            solar = g.get("solar")
            if solar:
                el += [Paragraph("Rooftop Solar Potential", ss["Sec"]), _kv([
                    ("Installable (kWp)", _n(solar["installable_kwp"])),
                    ("Annual generation (kWh)", _n(solar["annual_yield_kwh"])),
                    ("Annual saving", _n(solar["annual_saving_inr"])),
                    ("Payback (years)", _n(solar["payback_years"])),
                ])]

    # ---------------------------------------------------------------- sustainability
    if eng and report_type == "sustainability":
        mods = eng.get("modules") or {}
        green, carbon, trees = mods.get("green"), mods.get("carbon"), mods.get("trees")
        if green:
            el += [Paragraph("Green Rating", ss["Sec"]),
                   _kv([(o["label"], o["value"]) for o in green["outputs"]])]
        if carbon:
            el += [Paragraph("Embodied Carbon", ss["Sec"]),
                   _kv([(o["label"], f"{o['value']} {o['unit']}".strip())
                        for o in carbon["outputs"]]),
                   _table([["Material", "Quantity", "Unit", "Factor", "tCO2e", "Share"]] +
                          [[m["label"], _n(m["quantity"]), m["unit"], _n(m["factor"]),
                            _n(m["tco2e"]), f"{m['share_pct']}%"]
                           for m in carbon["materials"]],
                          col_widths=[48 * mm, 26 * mm, 16 * mm, 22 * mm, 24 * mm, 22 * mm])]
            if carbon.get("unpriced"):
                el += [Paragraph("Not carried in the carbon figure: "
                                 + ", ".join(carbon["unpriced"])
                                 + " — no defensible coefficient.", ss["Sub"])]
        if trees:
            el += [Paragraph("Plantation Plan", ss["Sec"]),
                   _kv([(o["label"], f"{o['value']} {o['unit']}".strip())
                        for o in trees["outputs"]]),
                   _table([["Zone", "Area (m²)", "Trees", "Species"]] +
                          [[z["zone"], _n(z["area_sqm"]), _n(z["trees"]),
                            ", ".join(sp["species"].split(" (")[0] for sp in z["species"])]
                           for z in trees["zones"]],
                          col_widths=[42 * mm, 24 * mm, 18 * mm, 74 * mm], align_right_from=4)]
        solar = (project.get("gis") or {}).get("solar")
        if solar:
            el += [Paragraph("Rooftop Solar", ss["Sec"]), _kv([
                ("Installable (kWp)", _n(solar["installable_kwp"])),
                ("Annual generation (kWh)", _n(solar["annual_yield_kwh"])),
                ("CO2 avoided (t/yr)", _n(solar["co2_avoided_tonnes_per_yr"])),
            ])]

    el += [Spacer(1, 10), Paragraph("Generated by Aptimizer — figures are estimates based on configurable "
                                    "thumb-rule ratios and project rule sets.", ss["Sub"])]
    doc.build(el)
    return buf.getvalue()


def build_all_pdf(project: dict, a: dict, eng: dict = None) -> bytes:
    """Every report in one document, behind a contents page.

    Built by concatenating the individual PDFs with pypdf rather than by assembling one
    giant story: each report already knows how to lay itself out, and rebuilding that
    inline would leave two definitions of every section to keep in step.
    """
    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()

    # Contents page, generated the same way the reports are so it matches them.
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    ss = _styles()
    el = [
        Paragraph("APTIMIZER", ParagraphStyle("brand", fontSize=10, textColor=BRAND, spaceAfter=2)),
        Paragraph("Complete Project Report Set", ss["H"]),
        Paragraph(f"Project: {project.get('name', '')} &nbsp;|&nbsp; Client: {project.get('client', '-')} "
                  f"&nbsp;|&nbsp; Location: {project.get('location', '-')} &nbsp;|&nbsp; "
                  f"Generated: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}", ss["Sub"]),
        Spacer(1, 10),
        Paragraph("Contents", ss["Sec"]),
    ]

    built = []
    for key in ALL_ORDER:
        try:
            built.append((key, build_pdf(key, project, a, eng)))
        except Exception:
            # One report failing must not cost the reader the other ten.
            continue

    page = 2                       # the contents page itself is page 1
    rows = [["#", "Report", "Page"]]
    for i, (key, pdf) in enumerate(built, 1):
        rows.append([str(i), REPORT_TITLES[key], str(page)])
        page += len(PdfReader(io.BytesIO(pdf)).pages)
    el += [_table(rows, col_widths=[14 * mm, 130 * mm, 20 * mm], align_right_from=3)]
    el += [Spacer(1, 10),
           Paragraph("Generated by Aptimizer — figures are estimates based on configurable "
                     "thumb-rule ratios and project rule sets.", ss["Sub"])]
    doc.build(el)

    writer.append(PdfReader(io.BytesIO(buf.getvalue())))
    for _key, pdf in built:
        writer.append(PdfReader(io.BytesIO(pdf)))

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


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
