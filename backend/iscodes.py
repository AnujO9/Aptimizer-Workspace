"""Single source of truth for every IS / NBC constant used by the engineering modules.
Update values here when a code is revised — no module hardcodes its own numbers.
"""

# ---------------------------------------------------------------- clause registry
CLAUSES = {
    "dead_load": {"code": "IS 875 (Part 1):1987", "clause": "Table 1", "topic": "Unit weights of building materials"},
    "live_load": {"code": "IS 875 (Part 2):1987", "clause": "Table 1", "topic": "Imposed loads — residential"},
    "roof_live": {"code": "IS 875 (Part 2):1987", "clause": "Cl. 4.1", "topic": "Imposed load on roofs"},
    "wind_speed": {"code": "IS 875 (Part 3):2015", "clause": "Cl. 6.2 / Fig. 1", "topic": "Basic wind speed"},
    "wind_k2": {"code": "IS 875 (Part 3):2015", "clause": "Table 2", "topic": "Terrain / height factor k2"},
    "wind_pressure": {"code": "IS 875 (Part 3):2015", "clause": "Cl. 7.2", "topic": "Design wind pressure pz = 0.6 Vz²"},
    "load_combo": {"code": "IS 456:2000", "clause": "Table 18", "topic": "Partial safety factors (1.5 DL + 1.5 LL)"},
    "column_design": {"code": "IS 456:2000", "clause": "Cl. 39.3", "topic": "Short axially loaded column with ties"},
    "column_min": {"code": "IS 456:2000", "clause": "Cl. 25.1.1", "topic": "Minimum column dimension 230 mm"},
    "beam_depth": {"code": "IS 456:2000", "clause": "Cl. 23.2.1", "topic": "Span/depth ratio (L/12 preliminary)"},
    "flat_slab": {"code": "IS 456:2000", "clause": "Cl. 31", "topic": "Flat slab applicability"},
    "seismic_zone": {"code": "IS 1893 (Part 1):2016", "clause": "Table 3 / Annex E", "topic": "Seismic zone factor Z"},
    "seismic_sa": {"code": "IS 1893 (Part 1):2016", "clause": "Cl. 6.4.2 / Fig. 2", "topic": "Design acceleration spectrum Sa/g"},
    "seismic_period": {"code": "IS 1893 (Part 1):2016", "clause": "Cl. 7.6.2", "topic": "Approximate fundamental period Ta"},
    "seismic_R": {"code": "IS 1893 (Part 1):2016", "clause": "Table 9", "topic": "Response reduction factor R"},
    "seismic_I": {"code": "IS 1893 (Part 1):2016", "clause": "Table 8", "topic": "Importance factor I"},
    "base_shear": {"code": "IS 1893 (Part 1):2016", "clause": "Cl. 7.6.1", "topic": "Design base shear VB = Ah × W"},
    "seismic_weight": {"code": "IS 1893 (Part 1):2016", "clause": "Cl. 7.4", "topic": "Seismic weight (DL + 25% LL)"},
    "ductile": {"code": "IS 13920:2016", "clause": "Cl. 1.1", "topic": "Ductile detailing for Zone III–V"},
    "sbc": {"code": "IS 6403:1981", "clause": "Cl. 5 / Table 1", "topic": "Safe bearing capacity of soils"},
    "rankine": {"code": "IS 6403:1981", "clause": "Cl. 5.1 (Rankine)", "topic": "Minimum depth of foundation"},
    "found_type": {"code": "IS 1904:1986", "clause": "Cl. 5", "topic": "Choice of foundation type"},
    "found_depth_min": {"code": "IS 1904:1986", "clause": "Cl. 6.1", "topic": "Minimum foundation depth 0.5 m"},
    "mix_target": {"code": "IS 10262:2019", "clause": "Cl. 4.2", "topic": "Target mean strength f'ck = fck + 1.65 S"},
    "mix_wc": {"code": "IS 456:2000", "clause": "Table 5", "topic": "Maximum free water-cement ratio by exposure"},
    "mix_cement": {"code": "IS 456:2000", "clause": "Table 5", "topic": "Minimum cement content by exposure"},
    "mix_water": {"code": "IS 10262:2019", "clause": "Table 4", "topic": "Water content for 25–50 mm slump"},
    "mix_ca": {"code": "IS 10262:2019", "clause": "Table 5", "topic": "Coarse aggregate volume (Zone II sand)"},
    "water_demand": {"code": "IS 1172:1993", "clause": "Cl. 4.1", "topic": "135 lpcd domestic + flushing + external"},
    "sewage": {"code": "IS 1172:1993", "clause": "Cl. 5", "topic": "Sewage generation = 80% of water supply"},
    "sump": {"code": "NBC 2016 Part 9", "clause": "Cl. 4.1.2", "topic": "Underground storage — one day demand"},
    "oht": {"code": "NBC 2016 Part 9", "clause": "Cl. 4.1.3", "topic": "Overhead tank — one-third day, min 2 compartments"},
    "fire_water": {"code": "NBC 2016 Part 4", "clause": "Table 7", "topic": "Static fire water storage for buildings > 15 m"},
    "stp": {"code": "NBC 2016 Part 9", "clause": "Cl. 5.4", "topic": "On-site sewage treatment requirement"},
    "storm_rational": {"code": "IS 3764 / NBC 2016 Part 9", "clause": "Cl. 4.3", "topic": "Rational method Q = CIA/360"},
    "storm_pipe": {"code": "NBC 2016 Part 9", "clause": "Cl. 4.4", "topic": "Storm drain sizing, self-cleansing velocity 0.6–3.0 m/s"},
    "rwh": {"code": "NBC 2016 Part 9 / IS 15797", "clause": "Cl. 4.5", "topic": "Rainwater harvesting mandatory above 200 m² plot"},
    "parking_ecs": {"code": "NBC 2016 Part 4 / SP:21", "clause": "Cl. 8.4", "topic": "1 ECS per 100 m² residential built-up"},
    "parking_ramp": {"code": "NBC 2016 Part 4", "clause": "Cl. 8.4.5", "topic": "Ramp gradient max 1:8, width 3.6 m / 6 m"},
    "parking_headroom": {"code": "NBC 2016 Part 4", "clause": "Cl. 8.4.4", "topic": "Basement clear headroom 2.4 m"},
    "parking_aisle": {"code": "SP:21", "clause": "Cl. 8.4.3", "topic": "6.0 m aisle for 90° bays"},
    "parking_accessible": {"code": "NBC 2016 Part 3 / RPwD Act 2016", "clause": "Cl. 13.4", "topic": "1 accessible bay per 50 spaces"},
    "parking_ev": {"code": "BEE / MoHUA EV Guidelines 2019", "clause": "Cl. 4.2", "topic": "20% EV-ready parking"},
    "parking_2w": {"code": "SP:21", "clause": "Cl. 8.4.2", "topic": "1 ECS = 3 two-wheeler spaces"},
    "fire_travel": {"code": "NBC 2016 Part 4", "clause": "Cl. 4.6.2", "topic": "Travel distance to exit ≤ 22.5 m (residential)"},
    "fire_stairs": {"code": "NBC 2016 Part 4", "clause": "Cl. 4.7", "topic": "Two staircases above 24 m, 1.5 m clear width"},
    "fire_refuge": {"code": "NBC 2016 Part 4", "clause": "Cl. 4.14", "topic": "Refuge area every 7th floor above 24 m"},
    "fire_ext": {"code": "NBC 2016 Part 4 / IS 2190", "clause": "Table 7", "topic": "1 extinguisher per 200 m² floor area"},
    "fire_lift": {"code": "NBC 2016 Part 4", "clause": "Cl. 4.9", "topic": "Fire lift above 30 m, stretcher car 1.1 × 2.1 m"},
    "fire_press": {"code": "NBC 2016 Part 4", "clause": "Cl. 4.7.6", "topic": "Stairwell pressurisation above 15 m"},
    "acc_ramp": {"code": "NBC 2016 Part 3", "clause": "Cl. 13.3", "topic": "Accessible ramp slope max 1:12"},
    "acc_door": {"code": "NBC 2016 Part 3", "clause": "Cl. 13.5", "topic": "Minimum clear door width 900 mm"},
    "acc_corridor": {"code": "NBC 2016 Part 3", "clause": "Cl. 13.6", "topic": "Corridor width 1200 mm min, 1500 mm preferred"},
    "acc_lift": {"code": "IS 3534 / NBC Part 3", "clause": "Cl. 13.7", "topic": "Lift car 1100 × 1400 mm minimum"},
    "acc_handrail": {"code": "NBC 2016 Part 3", "clause": "Cl. 13.3.4", "topic": "Dual handrails at 760 mm and 900 mm"},
    "acc_tactile": {"code": "NBC 2016 Part 3 / UNCRPD", "clause": "Cl. 13.9", "topic": "Tactile guiding path entrance to lift"},
    "griha": {"code": "GRIHA v2019", "clause": "Rating criteria", "topic": "GRIHA star rating thresholds"},
    "igbc": {"code": "IGBC Green Homes v3.0", "clause": "Rating criteria", "topic": "IGBC certification levels"},
    "grid": {"code": "IS 3861:2002", "clause": "Cl. 4", "topic": "Modular planning grid for apartments"},
}

# ---------------------------------------------------------------- IS 875 Part 1
UNIT_WEIGHTS = {  # kN/m³
    "rcc": 25.0, "pcc": 24.0, "brick_masonry": 19.2, "aac_block": 8.0,
    "cement_plaster": 20.4, "floor_finish": 24.0, "water": 10.0, "soil": 18.0,
}

# ---------------------------------------------------------------- IS 875 Part 2
LIVE_LOADS = {  # kN/m²
    "residential_room": 2.0, "corridor_stair": 3.0, "balcony": 3.0,
    "roof_inaccessible": 0.75, "roof_accessible": 1.5, "parking": 4.0,
}

# ---------------------------------------------------------------- IS 875 Part 3
WIND_K2 = [(10, 1.00), (15, 1.05), (20, 1.07), (30, 1.12), (50, 1.17), (100, 1.24), (150, 1.28), (200, 1.30)]
WIND_KD = 0.90  # Cl. 7.2.1 wind directionality
WIND_KA = 0.90  # Cl. 7.2.2 area averaging (typical > 100 m²)
WIND_KC = 0.90  # Cl. 7.3.3.13 combination factor

# ---------------------------------------------------------------- IS 1893:2016
ZONE_FACTOR = {"II": 0.10, "III": 0.16, "IV": 0.24, "V": 0.36}
SOIL_SEISMIC_TYPE = {
    "hard rock": "I", "gravel": "II", "dense sand": "II", "stiff clay": "II", "soft clay": "III",
}
RESPONSE_R = {"OMRF": 3.0, "SMRF": 5.0, "Shear wall": 4.0, "Dual system": 5.0, "Flat slab": 3.0}
IMPORTANCE_I = {"residential": 1.0, "important": 1.2, "critical": 1.5}

# ---------------------------------------------------------------- IS 6403 / IS 1904
SOILS = {
    "hard rock": {"sbc": 3240, "phi": 40, "gamma": 22.0, "label": "Hard rock"},
    "gravel": {"sbc": 440, "phi": 35, "gamma": 20.0, "label": "Gravel / coarse sand"},
    "dense sand": {"sbc": 440, "phi": 33, "gamma": 19.5, "label": "Dense sand"},
    "stiff clay": {"sbc": 180, "phi": 25, "gamma": 19.0, "label": "Stiff clay"},
    "soft clay": {"sbc": 100, "phi": 15, "gamma": 17.5, "label": "Soft / silty clay"},
}

# ---------------------------------------------------------------- IS 456 / IS 10262
EXPOSURE = {
    "mild": {"max_wc": 0.55, "min_cement": 300, "min_grade": 20, "cover": 20},
    "moderate": {"max_wc": 0.50, "min_cement": 300, "min_grade": 25, "cover": 30},
    "severe": {"max_wc": 0.45, "min_cement": 320, "min_grade": 30, "cover": 45},
    "very severe": {"max_wc": 0.45, "min_cement": 340, "min_grade": 35, "cover": 50},
}
MIX_STD_DEV = {20: 4.0, 25: 4.0, 30: 5.0, 35: 5.0, 40: 5.0}
MIX_WATER = {10: 208, 20: 186, 40: 165}          # IS 10262:2019 Table 4, 25–50 mm slump
MIX_CA_VOLUME = {10: 0.50, 20: 0.62, 40: 0.71}   # Table 5, Zone II sand, w/c 0.50
SG = {"cement": 3.15, "fine": 2.65, "coarse": 2.74, "water": 1.0}
CEMENT_TYPES = {"OPC 43": 43, "OPC 53": 53, "PPC": 43}

# ---------------------------------------------------------------- IS 1172 / NBC 9
WATER_LPCD = {"domestic": 135, "flushing": 45, "external": 15}
SEWAGE_FACTOR = 0.80
FIRE_STATIC_STORAGE_L = 50000     # NBC Part 4 Table 7, > 15 m
FIRE_RESERVE_IN_SUMP_L = 25000
OHT_FRACTION = 1 / 3
STP_TYPES = [(50, "SAFF (submerged aerated fixed film) — compact, low O&M"),
             (200, "SBR (sequential batch reactor) — best fit for mid-size projects"),
             (10 ** 9, "MBR (membrane bioreactor) — smallest footprint, highest reuse quality")]

# ---------------------------------------------------------------- storm water
RUNOFF_C = {"rcc_roof": 0.85, "paved": 0.80, "lawn": 0.20, "mixed_site": 0.60}
MANNING_N = 0.013
DRAIN_SLOPE = 1 / 120
RWH_MANDATORY_PLOT_SQM = 200

# ---------------------------------------------------------------- NBC parking
PARKING = {
    "ecs_per_sqm": 100.0, "max_ramp_pct": 12.5, "ramp_width_one_way": 3.6, "ramp_width_two_way": 6.0,
    "basement_headroom": 2.4, "aisle_90deg": 6.0, "accessible_per": 50, "ev_pct": 20.0,
    "two_wheeler_per_ecs": 3, "ecs_area": 23.0,
}

# ---------------------------------------------------------------- NBC fire
FIRE = {
    "max_travel_m": 22.5, "stair_min_width_m": 1.5, "two_stair_height_m": 24.0,
    "refuge_above_m": 24.0, "refuge_every_floors": 7, "extinguisher_per_sqm": 200.0,
    "fire_lift_above_m": 30.0, "fire_lift_car": (1.1, 2.1), "pressurisation_above_m": 15.0,
}

# ---------------------------------------------------------------- NBC accessibility
ACCESS = {
    "ramp_slope": 1 / 12, "door_width_mm": 900, "corridor_min_mm": 1200, "corridor_pref_mm": 1500,
    "lift_car_mm": (1100, 1400), "handrail_mm": (760, 900),
}

# ---------------------------------------------------------------- green rating
GREEN_CHECKLIST = [
    {"id": "site_topsoil", "category": "Site planning & land use", "label": "Topsoil preservation and reuse", "points": 4},
    {"id": "site_shading", "category": "Site planning & land use", "label": "Hardscape shading / cool roof", "points": 4},
    {"id": "site_native", "category": "Site planning & land use", "label": "Native landscaping ≥ 50% of soft area", "points": 4},
    {"id": "water_rwh", "category": "Water efficiency", "label": "Rainwater harvesting provided", "points": 6, "auto": "rwh"},
    {"id": "water_stp", "category": "Water efficiency", "label": "STP with treated-water reuse for flushing / landscape", "points": 6, "auto": "stp"},
    {"id": "water_fixtures", "category": "Water efficiency", "label": "Low-flow fixtures (≥ 30% reduction)", "points": 5},
    {"id": "water_meter", "category": "Water efficiency", "label": "Sub-metering of water systems", "points": 3},
    {"id": "energy_orientation", "category": "Energy efficiency", "label": "Optimal orientation / solar passive design", "points": 6},
    {"id": "energy_wwr", "category": "Energy efficiency", "label": "Window-to-wall ratio ≤ 40% with shading", "points": 5},
    {"id": "energy_renewable", "category": "Energy efficiency", "label": "On-site renewable (solar PV / SWH)", "points": 6},
    {"id": "energy_lighting", "category": "Energy efficiency", "label": "LED lighting + common-area controls", "points": 4},
    {"id": "mat_local", "category": "Materials", "label": "≥ 50% materials sourced within 400 km", "points": 5},
    {"id": "mat_recycled", "category": "Materials", "label": "Recycled content (fly-ash / GGBS concrete, AAC)", "points": 5},
    {"id": "mat_waste", "category": "Materials", "label": "Construction waste management plan", "points": 4},
    {"id": "iaq_ventilation", "category": "Indoor air quality", "label": "Cross ventilation in ≥ 90% habitable rooms", "points": 5},
    {"id": "iaq_lowvoc", "category": "Indoor air quality", "label": "Low-VOC paints and adhesives", "points": 4},
    {"id": "iaq_daylight", "category": "Indoor air quality", "label": "Daylight factor ≥ 2% in living areas", "points": 4},
]
GRIHA_BANDS = [(50, 1), (60, 2), (70, 3), (80, 4), (90, 5)]
IGBC_BANDS = [(40, "Certified"), (50, "Silver"), (60, "Gold"), (75, "Platinum")]

# ---------------------------------------------------------------- city reference data
# seismic zone (IS 1893 Annex E), basic wind speed m/s (IS 875-3 Annex A),
# annual rainfall mm and 1-hour design rainfall intensity mm/hr (IMD / NBC)
CITIES = {
    "Mumbai": ("Maharashtra", "III", 44, 2200, 90),
    "Pune": ("Maharashtra", "III", 39, 700, 60),
    "Nagpur": ("Maharashtra", "II", 44, 1100, 75),
    "Nashik": ("Maharashtra", "III", 39, 750, 60),
    "Thane": ("Maharashtra", "III", 44, 2100, 90),
    "Delhi": ("Delhi", "IV", 47, 790, 75),
    "New Delhi": ("Delhi", "IV", 47, 790, 75),
    "Gurugram": ("Haryana", "IV", 47, 700, 70),
    "Noida": ("Uttar Pradesh", "IV", 47, 750, 70),
    "Faridabad": ("Haryana", "IV", 47, 700, 70),
    "Chandigarh": ("Chandigarh", "IV", 47, 1100, 75),
    "Ludhiana": ("Punjab", "IV", 47, 750, 70),
    "Amritsar": ("Punjab", "IV", 47, 700, 70),
    "Jalandhar": ("Punjab", "IV", 47, 700, 70),
    "Bengaluru": ("Karnataka", "II", 33, 970, 60),
    "Mysuru": ("Karnataka", "II", 33, 800, 55),
    "Mangaluru": ("Karnataka", "III", 39, 3500, 100),
    "Hubballi": ("Karnataka", "III", 39, 800, 55),
    "Chennai": ("Tamil Nadu", "III", 50, 1400, 85),
    "Coimbatore": ("Tamil Nadu", "III", 39, 700, 60),
    "Madurai": ("Tamil Nadu", "II", 39, 850, 60),
    "Tiruchirappalli": ("Tamil Nadu", "II", 44, 850, 60),
    "Salem": ("Tamil Nadu", "III", 39, 900, 60),
    "Hyderabad": ("Telangana", "II", 44, 800, 65),
    "Warangal": ("Telangana", "II", 44, 900, 65),
    "Vijayawada": ("Andhra Pradesh", "III", 50, 1000, 75),
    "Visakhapatnam": ("Andhra Pradesh", "II", 50, 1100, 80),
    "Guntur": ("Andhra Pradesh", "III", 50, 900, 70),
    "Tirupati": ("Andhra Pradesh", "III", 50, 950, 70),
    "Kochi": ("Kerala", "III", 39, 3000, 100),
    "Thiruvananthapuram": ("Kerala", "III", 39, 1800, 90),
    "Kozhikode": ("Kerala", "III", 39, 3000, 100),
    "Thrissur": ("Kerala", "III", 39, 2900, 95),
    "Ahmedabad": ("Gujarat", "III", 39, 800, 70),
    "Surat": ("Gujarat", "III", 44, 1200, 80),
    "Vadodara": ("Gujarat", "III", 44, 930, 75),
    "Rajkot": ("Gujarat", "III", 39, 600, 65),
    "Bhuj": ("Gujarat", "V", 50, 350, 55),
    "Gandhinagar": ("Gujarat", "III", 39, 800, 70),
    "Jaipur": ("Rajasthan", "II", 47, 650, 65),
    "Jodhpur": ("Rajasthan", "II", 47, 360, 55),
    "Udaipur": ("Rajasthan", "II", 47, 640, 60),
    "Kota": ("Rajasthan", "II", 47, 800, 65),
    "Bhopal": ("Madhya Pradesh", "II", 39, 1150, 70),
    "Indore": ("Madhya Pradesh", "III", 39, 950, 70),
    "Jabalpur": ("Madhya Pradesh", "III", 47, 1350, 75),
    "Gwalior": ("Madhya Pradesh", "III", 47, 900, 70),
    "Lucknow": ("Uttar Pradesh", "III", 47, 1000, 70),
    "Kanpur": ("Uttar Pradesh", "III", 47, 820, 70),
    "Varanasi": ("Uttar Pradesh", "III", 47, 1100, 75),
    "Agra": ("Uttar Pradesh", "III", 47, 700, 70),
    "Prayagraj": ("Uttar Pradesh", "III", 47, 1000, 72),
    "Meerut": ("Uttar Pradesh", "IV", 47, 850, 70),
    "Dehradun": ("Uttarakhand", "IV", 47, 2100, 85),
    "Haridwar": ("Uttarakhand", "IV", 47, 1150, 80),
    "Shimla": ("Himachal Pradesh", "IV", 39, 1550, 75),
    "Srinagar": ("Jammu & Kashmir", "V", 39, 720, 60),
    "Jammu": ("Jammu & Kashmir", "IV", 47, 1100, 75),
    "Kolkata": ("West Bengal", "III", 50, 1600, 85),
    "Howrah": ("West Bengal", "III", 50, 1600, 85),
    "Siliguri": ("West Bengal", "IV", 47, 3200, 95),
    "Durgapur": ("West Bengal", "III", 47, 1400, 80),
    "Patna": ("Bihar", "IV", 47, 1100, 75),
    "Gaya": ("Bihar", "III", 47, 1100, 75),
    "Muzaffarpur": ("Bihar", "IV", 47, 1200, 78),
    "Ranchi": ("Jharkhand", "II", 47, 1400, 78),
    "Jamshedpur": ("Jharkhand", "II", 47, 1400, 78),
    "Bhubaneswar": ("Odisha", "III", 50, 1550, 85),
    "Cuttack": ("Odisha", "III", 50, 1500, 85),
    "Raipur": ("Chhattisgarh", "II", 39, 1250, 75),
    "Guwahati": ("Assam", "V", 50, 1700, 90),
    "Dibrugarh": ("Assam", "V", 50, 2700, 95),
    "Shillong": ("Meghalaya", "V", 50, 2800, 95),
    "Imphal": ("Manipur", "V", 47, 1450, 85),
    "Agartala": ("Tripura", "V", 50, 2100, 90),
    "Aizawl": ("Mizoram", "V", 50, 2500, 90),
    "Kohima": ("Nagaland", "V", 47, 2000, 88),
    "Gangtok": ("Sikkim", "IV", 47, 3500, 95),
    "Port Blair": ("Andaman & Nicobar", "V", 50, 3000, 100),
    "Panaji": ("Goa", "III", 39, 2900, 95),
    "Puducherry": ("Puducherry", "II", 50, 1250, 80),
}

STATE_FALLBACK = {
    "Maharashtra": ("III", 39, 1000, 70), "Karnataka": ("II", 33, 900, 60),
    "Tamil Nadu": ("III", 44, 1000, 70), "Kerala": ("III", 39, 2800, 95),
    "Telangana": ("II", 44, 850, 65), "Andhra Pradesh": ("III", 50, 1000, 75),
    "Gujarat": ("III", 44, 800, 70), "Rajasthan": ("II", 47, 550, 60),
    "Madhya Pradesh": ("II", 39, 1050, 70), "Uttar Pradesh": ("III", 47, 900, 72),
    "Uttarakhand": ("IV", 47, 1600, 82), "Himachal Pradesh": ("IV", 39, 1500, 75),
    "Punjab": ("IV", 47, 700, 70), "Haryana": ("IV", 47, 700, 70),
    "Delhi": ("IV", 47, 790, 75), "West Bengal": ("III", 50, 1600, 85),
    "Bihar": ("IV", 47, 1150, 76), "Jharkhand": ("II", 47, 1400, 78),
    "Odisha": ("III", 50, 1500, 85), "Chhattisgarh": ("II", 39, 1250, 75),
    "Assam": ("V", 50, 2200, 92), "Goa": ("III", 39, 2900, 95),
    "Jammu & Kashmir": ("V", 39, 800, 62),
}
DEFAULT_CITY_DATA = ("III", 39, 1000, 70)


# approximate city centres (lat, lng) — used to seed a new project's plot near its location
CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777), "Pune": (18.5204, 73.8567), "Nagpur": (21.1458, 79.0882),
    "Nashik": (19.9975, 73.7898), "Thane": (19.2183, 72.9781), "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090), "Gurugram": (28.4595, 77.0266), "Noida": (28.5355, 77.3910),
    "Faridabad": (28.4089, 77.3178), "Chandigarh": (30.7333, 76.7794), "Ludhiana": (30.9010, 75.8573),
    "Amritsar": (31.6340, 74.8723), "Jalandhar": (31.3260, 75.5762), "Bengaluru": (12.9716, 77.5946),
    "Mysuru": (12.2958, 76.6394), "Mangaluru": (12.9141, 74.8560), "Hubballi": (15.3647, 75.1240),
    "Chennai": (13.0827, 80.2707), "Coimbatore": (11.0168, 76.9558), "Madurai": (9.9252, 78.1198),
    "Tiruchirappalli": (10.7905, 78.7047), "Salem": (11.6643, 78.1460), "Hyderabad": (17.3850, 78.4867),
    "Warangal": (17.9689, 79.5941), "Vijayawada": (16.5062, 80.6480), "Visakhapatnam": (17.6868, 83.2185),
    "Guntur": (16.3067, 80.4365), "Tirupati": (13.6288, 79.4192), "Kochi": (9.9312, 76.2673),
    "Thiruvananthapuram": (8.5241, 76.9366), "Kozhikode": (11.2588, 75.7804), "Thrissur": (10.5276, 76.2144),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311), "Vadodara": (22.3072, 73.1812),
    "Rajkot": (22.3039, 70.8022), "Bhuj": (23.2420, 69.6669), "Gandhinagar": (23.2156, 72.6369),
    "Jaipur": (26.9124, 75.7873), "Jodhpur": (26.2389, 73.0243), "Udaipur": (24.5854, 73.7125),
    "Kota": (25.2138, 75.8648), "Bhopal": (23.2599, 77.4126), "Indore": (22.7196, 75.8577),
    "Jabalpur": (23.1815, 79.9864), "Gwalior": (26.2183, 78.1828), "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319), "Varanasi": (25.3176, 82.9739), "Agra": (27.1767, 78.0081),
    "Prayagraj": (25.4358, 81.8463), "Meerut": (28.9845, 77.7064), "Dehradun": (30.3165, 78.0322),
    "Haridwar": (29.9457, 78.1642), "Shimla": (31.1048, 77.1734), "Srinagar": (34.0837, 74.7973),
    "Jammu": (32.7266, 74.8570), "Kolkata": (22.5726, 88.3639), "Howrah": (22.5958, 88.2636),
    "Siliguri": (26.7271, 88.3953), "Durgapur": (23.5204, 87.3119), "Patna": (25.5941, 85.1376),
    "Gaya": (24.7955, 85.0002), "Muzaffarpur": (26.1209, 85.3647), "Ranchi": (23.3441, 85.3096),
    "Jamshedpur": (22.8046, 86.2029), "Bhubaneswar": (20.2961, 85.8245), "Cuttack": (20.4625, 85.8830),
    "Raipur": (21.2514, 81.6296), "Guwahati": (26.1445, 91.7362), "Dibrugarh": (27.4728, 94.9120),
    "Shillong": (25.5788, 91.8933), "Imphal": (24.8170, 93.9368), "Agartala": (23.8315, 91.2868),
    "Aizawl": (23.7271, 92.7176), "Kohima": (25.6751, 94.1086), "Gangtok": (27.3314, 88.6138),
    "Port Blair": (11.6234, 92.7265), "Panaji": (15.4909, 73.8278), "Puducherry": (11.9416, 79.8083),
}
DEFAULT_CENTER = (12.9716, 77.5946)


def city_center(location):
    """Best-effort lat/lng for a free-text or dropdown location string."""
    key = (location or "").strip()
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    low = key.lower()
    for city, c in CITY_COORDS.items():
        if city.lower() in low:
            return c
    return DEFAULT_CENTER


def city_reference(city, state=""):
    key = (city or "").strip().title()
    if key in CITIES:
        st, zone, wind, rain, intensity = CITIES[key]
        return {"city": key, "state": st, "zone": zone, "wind_speed": wind,
                "annual_rainfall_mm": rain, "rain_intensity_mm_hr": intensity, "source": "city"}
    st = (state or "").strip().title()
    if st in STATE_FALLBACK:
        zone, wind, rain, intensity = STATE_FALLBACK[st]
        return {"city": key or st, "state": st, "zone": zone, "wind_speed": wind,
                "annual_rainfall_mm": rain, "rain_intensity_mm_hr": intensity, "source": "state"}
    zone, wind, rain, intensity = DEFAULT_CITY_DATA
    return {"city": key, "state": st, "zone": zone, "wind_speed": wind,
            "annual_rainfall_mm": rain, "rain_intensity_mm_hr": intensity, "source": "default"}


# ---------------------------------------------------------------- searchable library
CODE_LIBRARY = [
    {"id": "is456", "code": "IS 456:2000", "topic": "Plain & reinforced concrete — code of practice",
     "key_value": "M20 min grade for RCC; cover 20–50 mm by exposure; span/depth 20 (SS), 26 (cont.)",
     "clause": "Table 5, Cl. 23.2.1, Cl. 39.3"},
    {"id": "is875_1", "code": "IS 875 (Part 1):1987", "topic": "Dead loads — unit weights",
     "key_value": "RCC 25 kN/m³, brick masonry 19.2 kN/m³, AAC 8 kN/m³, plaster 20.4 kN/m³", "clause": "Table 1"},
    {"id": "is875_2", "code": "IS 875 (Part 2):1987", "topic": "Imposed (live) loads",
     "key_value": "Residential rooms 2.0 kN/m²; corridors/stairs 3.0; inaccessible roof 0.75; accessible roof 1.5",
     "clause": "Table 1, Cl. 4.1"},
    {"id": "is875_3", "code": "IS 875 (Part 3):2015", "topic": "Wind loads",
     "key_value": "Vb 33–55 m/s by region; pz = 0.6 Vz²; k2 from Table 2; Kd 0.90", "clause": "Cl. 6.2, 7.2"},
    {"id": "is1893", "code": "IS 1893 (Part 1):2016", "topic": "Earthquake resistant design",
     "key_value": "Z = 0.10/0.16/0.24/0.36 for Zone II/III/IV/V; VB = Ah·W; Ah = Z·I·Sa/g ÷ 2R",
     "clause": "Table 3, Cl. 6.4.2, 7.6.1"},
    {"id": "is13920", "code": "IS 13920:2016", "topic": "Ductile detailing of RC structures",
     "key_value": "Mandatory for Zone III, IV, V and for all important structures", "clause": "Cl. 1.1"},
    {"id": "is1172", "code": "IS 1172:1993", "topic": "Water supply & drainage requirements",
     "key_value": "135 lpcd domestic (+45 flushing, +15 external); sewage = 80% of supply", "clause": "Cl. 4.1, 5"},
    {"id": "is10262", "code": "IS 10262:2019", "topic": "Concrete mix proportioning",
     "key_value": "f'ck = fck + 1.65S; water 186 l/m³ for 20 mm agg; CA volume 0.62 (Zone II, w/c 0.50)",
     "clause": "Cl. 4.2, Table 4, Table 5"},
    {"id": "is6403", "code": "IS 6403:1981", "topic": "Bearing capacity of shallow foundations",
     "key_value": "SBC: rock 3240, gravel/dense sand 440, stiff clay 180, soft clay 100 kN/m²", "clause": "Cl. 5, Table 1"},
    {"id": "is1904", "code": "IS 1904:1986", "topic": "Design & construction of foundations",
     "key_value": "Minimum depth 0.5 m below NGL; footing type by load and soil", "clause": "Cl. 5, 6.1"},
    {"id": "is3764", "code": "IS 3764:1992 / NBC Part 9", "topic": "Storm water drainage",
     "key_value": "Rational method Q = CIA/360; C = 0.85 RCC roof; velocity 0.6–3.0 m/s", "clause": "Cl. 4.3, 4.4"},
    {"id": "is3861", "code": "IS 3861:2002", "topic": "Method of measurement / apartment planning minimums",
     "key_value": "Habitable room min 9.5 m², kitchen 5.5 m², bath 1.8 m², min width 2.4 m", "clause": "Cl. 4"},
    {"id": "is3534", "code": "IS 3534 / NBC Part 3", "topic": "Lift car dimensions for accessibility",
     "key_value": "Minimum accessible lift car 1100 × 1400 mm, door 900 mm", "clause": "Cl. 13.7"},
    {"id": "nbc3", "code": "NBC 2016 Part 3", "topic": "Development control, FAR, setbacks, accessibility",
     "key_value": "Ramp 1:12; door 900 mm; corridor 1200 mm (1500 preferred); 1 accessible bay per 50",
     "clause": "Cl. 8, 13"},
    {"id": "nbc4", "code": "NBC 2016 Part 4", "topic": "Fire & life safety",
     "key_value": "Travel 22.5 m; 2 stairs > 24 m at 1.5 m width; refuge every 7th floor > 24 m; fire lift > 30 m",
     "clause": "Cl. 4.6, 4.7, 4.9, 4.14"},
    {"id": "nbc8", "code": "NBC 2016 Part 8 / SP:21", "topic": "Building services & parking",
     "key_value": "1 ECS per 100 m² built-up; ramp 1:8; headroom 2.4 m; aisle 6.0 m; 1 ECS = 3 two-wheelers",
     "clause": "Cl. 8.4"},
    {"id": "nbc9", "code": "NBC 2016 Part 9", "topic": "Plumbing services, water & waste",
     "key_value": "Sump = 1 day demand + fire reserve; OHT = 1/3 day in ≥ 2 compartments; RWH > 200 m² plot",
     "clause": "Cl. 4.1–4.5"},
    {"id": "griha", "code": "GRIHA v2019 / IGBC Green Homes v3.0", "topic": "Green building rating",
     "key_value": "GRIHA 1★ ≥ 50 pts … 5★ ≥ 90; IGBC Certified 40, Silver 50, Gold 60, Platinum 75",
     "clause": "Rating criteria"},
    {"id": "bee_ev", "code": "MoHUA / BEE EV Guidelines 2019", "topic": "EV charging infrastructure",
     "key_value": "20% of parking spaces to be EV-ready with dedicated feeder capacity", "clause": "Cl. 4.2"},
    {"id": "rpwd", "code": "RPwD Act 2016 / Harmonised Guidelines 2021", "topic": "Barrier-free access",
     "key_value": "Accessible parking, ramps, tactile paths and signage mandatory in group housing",
     "clause": "Ch. 3"},
]

CODE_INDEX = {c["id"]: c for c in CODE_LIBRARY}

# extra search keywords so a query like "seismic" or "parking" finds the right standard
CODE_KEYWORDS = {
    "is456": "rcc concrete design cover span depth column beam grade",
    "is875_1": "dead load unit weight masonry density",
    "is875_2": "live load imposed load residential roof corridor",
    "is875_3": "wind load wind speed pressure terrain",
    "is1893": "seismic earthquake zone base shear zone factor spectrum soil",
    "is13920": "seismic ductile detailing earthquake confinement",
    "is1172": "water demand lpcd sewage plumbing supply",
    "is10262": "mix design concrete proportion water cement ratio aggregate",
    "is6403": "soil bearing capacity sbc foundation footing",
    "is1904": "foundation footing raft pile depth soil",
    "is3764": "storm water drainage rainfall runoff rational method rainwater harvesting recharge",
    "is3861": "apartment planning room size measurement grid modular",
    "is3534": "lift elevator accessibility car size",
    "nbc3": "far setback accessibility ramp corridor door barrier free development control",
    "nbc4": "fire safety travel distance staircase refuge extinguisher fire lift pressurisation",
    "nbc8": "parking ecs ramp headroom aisle two wheeler services",
    "nbc9": "water sump overhead tank stp rainwater harvesting plumbing drainage",
    "griha": "green building rating griha igbc energy water materials",
    "bee_ev": "ev electric vehicle charging parking",
    "rpwd": "accessibility disabled barrier free tactile accessible parking",
}
for _id, _kw in CODE_KEYWORDS.items():
    if _id in CODE_INDEX:
        CODE_INDEX[_id]["keywords"] = _kw
CODE_BY_STANDARD = {}
for _c in CODE_LIBRARY:
    CODE_BY_STANDARD.setdefault(_c["code"].split(":")[0].strip(), _c["id"])

# clauses that cite two standards at once cannot be resolved by prefix — map them explicitly
CLAUSE_LIBRARY = {
    "storm_rational": "is3764", "rwh": "nbc9", "parking_ecs": "nbc8", "parking_aisle": "nbc8",
    "parking_accessible": "rpwd", "parking_ev": "bee_ev", "parking_2w": "nbc8", "fire_ext": "nbc4",
    "acc_tactile": "nbc3", "griha": "griha", "igbc": "griha",
}


def clause(key):
    """Inline clause reference + the library entry it deep-links to."""
    c = CLAUSES.get(key)
    if not c:
        return None
    std = c["code"].split(":")[0].strip()
    return {**c, "library_id": CLAUSE_LIBRARY.get(key) or CODE_BY_STANDARD.get(std)}
