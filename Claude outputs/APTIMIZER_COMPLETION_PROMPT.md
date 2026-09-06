# Aptimizer Feature Completion Guide
## Strategic Implementation Pathway for Partial Features (V1 → V4+)

**Last Updated:** September 5, 2026  
**Scope:** 28 Partially-Built Features across V1–X+ | 324/420 Features Complete (77%)  
**Target:** Production-ready V1–V3, V4 foundation, V5 roadmap  

---

## PART 1: COMPLETION STRATEGY

### Guiding Principles
1. **Vertical Completion First**: Complete V1 and V2.5 before moving to V4. V3 engineering modules are stable.
2. **Dependency Ordering**: Genetic algorithm (stage 3b) blocks advanced site layout; implement only if timeline permits.
3. **Frontend-Backend Sync**: Every backend completion requires a matching frontend module update.
4. **Testing at Completion**: Each feature gets validation against the methodology in the Feature List PDF.
5. **Code Hygiene**: All NBC 2016 references must be catalogued; SP 7:2026 migration tracked separately.

### Three Implementation Tiers

| Tier | Scope | Timeline | Impact |
|------|-------|----------|--------|
| **Tier 1 (Quick Wins)** | 12 features close to completion; missing <10% | 2–3 weeks | Pushes completion to 85%+ |
| **Tier 2 (Core V4)** | 8 features + collaboration framework | 4–6 weeks | Enables multi-user workflows |
| **Tier 3 (V5 Foundation)** | 6 features + BIM interop; partial V5 | 8–12 weeks | Sets stage for digital twin |

---

## PART 2: TIER 1 QUICK WINS (Immediate Completion)

### 1. **Genetic Algorithm Site Packing (Stage 3b)** — `backend/siteplan/__init__.py`
**Status:** Greedy grid implemented; genetic refinement marked `[next]`  
**Current State:**  
- Lines 1–150: Envelope generation ✓  
- Lines 150–280: Reserve allocation ✓  
- Lines 280–450: Greedy grid packing ✓  
- Lines 450–550: Genetic refinement [TODO]  

**What's Missing:**
- Fitness function (tower placement, setbacks, unit count, solar exposure, wind)
- Crossover/mutation operators for tower position, footprint, height
- Multi-objective optimization (maximize units + minimize footprint + solar access)
- Convergence criteria and population size tuning

**Implementation Path:**
```python
# File: backend/siteplan/optimize.py (NEW)
class FitnessEvaluator:
    def __init__(self, envelope, site_params):
        self.envelope = envelope
        self.setbacks = site_params['setbacks']
    
    def fitness(self, towers):
        """Multi-objective: units + setbacks + solar + wind"""
        units = sum(t.units for t in towers)
        setback_penalty = self._setback_violations(towers)
        solar_bonus = self._solar_exposure(towers)
        wind_penalty = self._wind_load_variance(towers)
        return units - setback_penalty + solar_bonus - wind_penalty

class GeneticOptimizer:
    def __init__(self, fitness_fn, population_size=50, generations=100):
        self.fitness = fitness_fn
        self.pop_size = population_size
        self.gens = generations
    
    def optimize(self, initial_solution):
        """Run GA refinement over greedy initial solution"""
        population = self._initialize(initial_solution)
        for gen in range(self.gens):
            fitness_scores = [self.fitness(ind) for ind in population]
            population = self._select(population, fitness_scores)
            population = self._crossover(population)
            population = self._mutate(population)
        return max(population, key=self.fitness)
```

**Validation Strategy:** Generate 10 test plots (500–2000 m²); compare greedy vs. genetic solutions on unit count, setback compliance, and solar exposure.

**Effort:** 3–4 days  
**Blockers:** None (fitness.py exists; integrate it)

---

### 2. **Revit/DWG Export** — `backend/bim_export.py` (NEW)
**Status:** 0% (V5 feature, but can be prototyped early)  
**Requirement:** Output building envelope, towers, slab layout, MEP zones as industry-standard formats

**What's Missing:**
- Revit API integration (pyrevit or RevitPythonWrapper)
- DWG generation via ezdxf library
- Slab geometry export with floor tagging
- MEP zone mapping (electrical, plumbing, HVAC by floor)

**Implementation Path:**
```python
# File: backend/bim_export.py (NEW)
import ezdxf
from ezdxf.addons import DxfDocument

class RevitExporter:
    def __init__(self, building):
        self.building = building
        self.doc = ezdxf.new(dxfversion='R2018')
    
    def export(self, filepath):
        """Export building as DWG with layers per system"""
        msp = self.doc.modelspace()
        
        # Add envelope
        self._draw_envelope(msp)
        
        # Add towers and footprints
        for tower in self.building.towers:
            self._draw_tower(msp, tower)
        
        # Add slabs
        for level in self.building.levels:
            self._draw_slab(msp, level)
        
        # Add MEP zones
        self._draw_mep_zones(msp)
        
        self.doc.saveas(filepath)
    
    def _draw_envelope(self, msp):
        """Envelope as boundary polyline"""
        env_points = [(p.x, p.y) for p in self.building.envelope]
        msp.add_lwpolyline(env_points, dxfattribs={'layer': 'BOUNDARY'})
```

**Validation Strategy:** Export a V1 building; open in AutoCAD; verify layer structure, coordinates, and geometry match.

**Effort:** 2–3 days  
**Blockers:** Requires AutoCAD/DWG knowledge; use ezdxf library (free, well-documented).

---

### 3. **Water Demand Validation** — `backend/engine.py:water_demand()`
**Status:** 90% (formula exists; validation cases missing)  
**Current Implementation:**  
```python
def water_demand(self):
    lpd = 135  # IS 1172 litres per capita per day
    occ = self.occupancy()  # persons
    daily = lpd * occ
    return daily, daily * 1.5  # avg, peak
```

**What's Missing:**
- Distinguish residential vs. commercial occupancy rates
- Peak factor by building type (residential: 1.5–2.0; commercial: 1.3–1.5)
- Daylight hours storage (IS 1172 Table 1)
- Fire demand integration (m8_fire.py provides fire_demand_L)
- Rainwater harvest offset calculation

**Implementation Path:**
```python
# Extend backend/engine.py:water_demand()
def water_demand(self, building_type='residential'):
    """IS 1172 water demand with fire integration"""
    if building_type == 'residential':
        lpd = 135  # Table 1
        peak_factor = 1.8
        occ = self.occupancy('residential')
    else:  # commercial
        lpd = 25  # per 100 m² built-up
        peak_factor = 1.3
        occ = self.occupancy('commercial')
    
    daily = lpd * occ
    peak = daily * peak_factor
    
    # Add fire demand (from m8_fire)
    fire_demand = self.fire_module.fire_water_demand()
    
    # Subtract rainwater harvest credit
    rainfall_mm = self.site.annual_rainfall()
    harvest_area = self.building.roof_area()
    harvest_annual = (rainfall_mm / 1000) * harvest_area * 0.75  # 75% efficiency
    
    return {
        'daily_lpd': daily,
        'peak_lph': peak,
        'fire_demand_l': fire_demand,
        'harvest_credit_l': harvest_annual / 365,
        'net_demand_lpd': daily + fire_demand / 365 - harvest_annual / 365
    }
```

**Validation Strategy:** Test against IS 1172 examples (Table 1: 100-person residential = 13,500 L/day; peak 2.0 = 27,000 L/peak-hour). Compare Aptimizer output.

**Effort:** 1–2 days  
**Blockers:** None; fire_module already exists.

---

### 4. **Green Rating Integration** — `backend/ratings.py` (EXPAND)
**Status:** 60% (IGBC/GRIHA framework exists; scoring incomplete)  
**Current State:** Tracks embodied carbon; missing IGBC prerequisites and GRIHA point calculation

**What's Missing:**
- IGBC mandatory prerequisites (IAQ, energy baseline, water efficiency)
- GRIHA point calculation (energy, water, waste, materials, innovation)
- Rating translation (IGBC Gold/Platinum; GRIHA 3-star/5-star)
- Credits for features already built (solar PV bonus, rainwater harvest, waste sorting)

**Implementation Path:**
```python
# File: backend/ratings.py (EXPAND)
class IGBCEvaluator:
    PREREQUISITES = {
        'iaq': {'points': 0, 'mandatory': True},  # Commissioning, VOC limits
        'energy': {'baseline': 'ASHRAE 90.1', 'mandatory': True},
        'water': {'baseline': 'IS 1172 + 20% reduction', 'mandatory': True},
    }
    
    def evaluate(self, building):
        """Score IGBC points and determine rating"""
        credits = []
        
        # Energy: solar PV, daylighting, chiller efficiency
        if building.solar_kwp > 0:
            credits.append(('Renewable Energy', 7 * (building.solar_kwp / building.power_demand_kw)))
        
        # Water: rainwater, recycled, reduced fixtures
        if building.rainwater_harvest_lpd > 0:
            credits.append(('Water Efficiency', 5 * (building.rainwater_harvest_lpd / building.water_demand_lpd)))
        
        # Materials: recycled content, embodied carbon
        if building.embodied_carbon_kgco2 < self.baseline_carbon(building):
            reduction = 1 - building.embodied_carbon_kgco2 / self.baseline_carbon(building)
            credits.append(('Materials & Waste', 6 * reduction))
        
        # Innovation: thesis project, novel design
        credits.append(('Innovation', 2 if building.project_type == 'thesis' else 0))
        
        total_points = sum(pts for _, pts in credits)
        rating = self._points_to_rating(total_points)
        
        return {'credits': credits, 'total_points': total_points, 'rating': rating}
    
    def _points_to_rating(self, points):
        if points >= 80: return 'Platinum'
        if points >= 60: return 'Gold'
        if points >= 40: return 'Silver'
        return 'Certified'
```

**Validation Strategy:** Score a completed V1 building against IGBC criteria published by CII; compare to manual checklist.

**Effort:** 2–3 days  
**Blockers:** Requires IGBC criteria document (freely available on CII website).

---

### 5. **CPM Float Verification** — `backend/schedule.py`
**Status:** 95% (critical path calculated; float validation incomplete)  
**Current State:** Returns critical path; missing verification that all forward/backward passes agree

**What's Missing:**
- Backward pass validation (ensure LS + duration = LF for all tasks)
- Free float vs. total float distinction
- Critical path highlighting (tasks with 0 total float)
- Lag/lead management (FS, SS, FF, SF relationships)

**Implementation Path:**
```python
# File: backend/schedule.py (EXPAND)
def verify_float(schedule):
    """Verify all float calculations are internally consistent"""
    errors = []
    for task in schedule.tasks:
        # Check backward pass: LS + duration = LF
        if task.LS + task.duration != task.LF:
            errors.append(f"Task {task.id}: backward pass mismatch")
        
        # Check forward pass: ES + duration = EF
        if task.ES + task.duration != task.EF:
            errors.append(f"Task {task.id}: forward pass mismatch")
        
        # Calculate and verify float
        total_float = task.LS - task.ES
        free_float = min([succ.ES - task.EF for succ in task.successors]) if task.successors else 0
        
        if total_float < 0:
            errors.append(f"Task {task.id}: negative total float (schedule is infeasible)")
        
        if free_float < 0:
            errors.append(f"Task {task.id}: negative free float")
    
    return {'valid': len(errors) == 0, 'errors': errors}
```

**Validation Strategy:** Create a 10-task test schedule; manually calculate float; compare to Aptimizer output.

**Effort:** 1 day  
**Blockers:** None; schedule.py already exists.

---

### 6. **Unit Mix Optimization** — `backend/planning.py`
**Status:** 70% (unit count calculated; mix not optimized for revenue)  
**Current State:** Returns total units and area; missing breakdown by unit type (1BHK, 2BHK, 3BHK, etc.)

**What's Missing:**
- Unit type definitions (area, parking ratio, common factor)
- Revenue/salability by location (premium on higher floors, corner units)
- Mix optimization for target revenue or target demographic

**Implementation Path:**
```python
# File: backend/planning.py (EXPAND)
class UnitPlanner:
    UNIT_TYPES = {
        '1BHK': {'area': 45, 'parking': 0.8, 'common': 1.25},
        '2BHK': {'area': 75, 'parking': 1.0, 'common': 1.30},
        '3BHK': {'area': 130, 'parking': 1.5, 'common': 1.35},
    }
    
    def optimize_mix(self, total_units, total_area, revenue_target=None):
        """Find unit mix that fits area and maximizes revenue or meets demographic target"""
        from scipy.optimize import linprog
        
        # Decision variables: count of each unit type
        # Constraint: total area used ≤ total_area * (1 + common factor)
        # Objective: maximize revenue or meet demographic target
        
        mix = {}
        current_area = 0
        for unit_type in ['3BHK', '2BHK', '1BHK']:  # Greedy from largest
            spec = self.UNIT_TYPES[unit_type]
            units_possible = int((total_area - current_area) / (spec['area'] * spec['common']))
            units_to_build = min(units_possible, total_units - sum(mix.values()))
            mix[unit_type] = units_to_build
            current_area += units_to_build * spec['area'] * spec['common']
        
        return mix
```

**Validation Strategy:** Test: 100 units in 8,000 m² → expect ~30% 3BHK, 50% 2BHK, 20% 1BHK. Verify against real project typologies.

**Effort:** 1–2 days  
**Blockers:** None; planning.py exists.

---

### 7. **Sector-Based Unit Placement (Vastu)** — `backend/planning.py:vastu_placement()`
**Status:** 60% (sectors defined; placement logic needs refinement)  
**Current State:** Assigns units by Vastu direction; missing optimization for view, orientation, corner premium

**What's Missing:**
- View quality scoring (North/South facing as premium)
- Orientation preference by unit type (living room faces view; service areas away from view)
- Corner unit premium pricing
- Accessibility constraints (ground floor for mobility-impaired)

**Implementation Path:**
```python
# File: backend/planning.py (EXPAND)
def vastu_placement(towers, all_units, site_params):
    """Assign units to towers/floors respecting Vastu + orientation + premium"""
    vastu_sectors = {
        'north': {'view_quality': 0.9, 'price_multiplier': 1.15},
        'south': {'view_quality': 0.7, 'price_multiplier': 0.95},
        'east': {'view_quality': 0.8, 'price_multiplier': 1.05},
        'west': {'view_quality': 0.6, 'price_multiplier': 0.90},
    }
    
    placement = {}
    premium_units = [u for u in all_units if u.type == '3BHK']
    
    for unit in all_units:
        # Preference: premium units in high-quality sectors
        if unit in premium_units:
            sector = 'north'  # Best view
            floor = 'upper'   # Command premium
        else:
            sector = 'east'   # Secondary preference
            floor = 'middle'
        
        placement[unit.id] = {
            'tower': towers[0],
            'floor': floor,
            'sector': sector,
            'price_adj': vastu_sectors[sector]['price_multiplier']
        }
    
    return placement
```

**Validation Strategy:** Place 100 units across 2 towers; verify Vastu rules (no toilets in North, prayer room in NE, etc.). Compare manual placement.

**Effort:** 1–2 days  
**Blockers:** None; requires Vastu principle documentation (readily available).

---

### 8. **Embodied Carbon Baseline** — `backend/sustainability.py`
**Status:** 80% (calculation exists; baseline not defined)  
**Current State:** Calculates embodied carbon for materials; no baseline for comparison or reduction target

**What's Missing:**
- National baseline by building type and year (EC1 = embodied carbon at completion)
- Material substitution tracking (steel → timber, concrete → recycled concrete)
- Reduction target calculation (e.g., 30% below baseline = 6 IGBC credits)

**Implementation Path:**
```python
# File: backend/sustainability.py (EXPAND)
EMBODIED_CARBON_BASELINE = {
    'residential': {2025: 650, 2026: 640},  # kg CO2e / m² GFA, declining annually
    'commercial': {2025: 750, 2026: 730},
    'mixed': {2025: 700, 2026: 680},
}

def calculate_carbon_reduction_target(building, target_pct=30):
    """Calculate embodied carbon reduction needed for green rating"""
    baseline = EMBODIED_CARBON_BASELINE[building.type][building.completion_year]
    baseline_total = baseline * building.gfa
    
    target_total = baseline_total * (1 - target_pct / 100)
    actual_total = building.embodied_carbon_kgco2
    
    reduction_needed = baseline_total - target_total
    reduction_achieved = baseline_total - actual_total
    
    return {
        'baseline_kgco2': baseline_total,
        'target_kgco2': target_total,
        'actual_kgco2': actual_total,
        'reduction_needed_kgco2': reduction_needed,
        'reduction_achieved_kgco2': reduction_achieved,
        'target_met': reduction_achieved >= reduction_needed,
    }
```

**Validation Strategy:** Compare building embodied carbon to EC1 baseline; calculate IGBC credit score.

**Effort:** 1 day  
**Blockers:** Requires baseline data (from EN 15978 or national LCA database).

---

### 9. **Parking Layout Generation** — `backend/planning.py:parking_layout()`
**Status:** 50% (stall count calculated; layout generation missing)  
**Current State:** Returns parking requirement (1 stall per X units); missing actual layout, aisle width, turning radius

**What's Missing:**
- Parking typology: basement vs. podium vs. surface
- Stall arrangement: herringbone, perpendicular, parallel
- Aisle widths per NBC (3.5 m for one-way, 6.0 m for two-way)
- EV charging zones (20% of spaces per MoHUA guideline)
- Accessible parking (1 per 25 stalls per IS 16001)

**Implementation Path:**
```python
# File: backend/planning.py (EXPAND)
class ParkingPlanner:
    STALL_WIDTHS = {'parallel': 2.4, 'perpendicular': 2.8, 'herringbone': 2.6}
    AISLE_WIDTHS = {'one_way': 3.5, 'two_way': 6.0}
    
    def layout_parking(self, total_stalls, typology='basement', arrangement='herringbone'):
        """Generate parking layout with stall positions"""
        stall_width = self.STALL_WIDTHS[arrangement]
        stall_depth = 5.5  # Standard
        aisle_width = self.AISLE_WIDTHS['one_way'] if typology == 'basement' else 6.0
        
        # Arrange in bays
        stalls_per_row = 10
        rows = (total_stalls + stalls_per_row - 1) // stalls_per_row
        
        width = stalls_per_row * stall_width + aisle_width
        length = rows * stall_depth
        area_m2 = width * length
        
        # Add EV charging (20%)
        ev_stalls = int(total_stalls * 0.20)
        
        # Add accessible (1 per 25)
        accessible_stalls = max(1, total_stalls // 25)
        
        return {
            'total_stalls': total_stalls,
            'ev_stalls': ev_stalls,
            'accessible_stalls': accessible_stalls,
            'layout_area_m2': area_m2,
            'width_m': width,
            'length_m': length,
        }
```

**Validation Strategy:** Layout 100 stalls; verify area against NBC (typically 25–30 m² per stall including circulation).

**Effort:** 1–2 days  
**Blockers:** None; planning.py exists.

---

### 10. **Cost Breakdown Structure (BOQ Export)** — `backend/boq.py`
**Status:** 75% (rates database exists; BOQ formatting incomplete)  
**Current State:** Calculates aggregate costs; missing line-item BOQ for tendering

**What's Missing:**
- Structured BOQ export (CSV, Excel with schedules)
- Rate book lookup by location (Delhi, Mumbai, Pune, etc.)
- Escalation factors by material (cement +2% annually; steel +3% annually)
- Contingency allocation (typically 10–15% for unforeseen)

**Implementation Path:**
```python
# File: backend/boq.py (EXPAND)
class BOQExporter:
    def export_bom(self, building, rate_book='delhi_2026', format='excel'):
        """Export Bill of Quantities with rates and contingency"""
        boq_items = []
        total_cost = 0
        
        # Concrete (m3)
        concrete_vol = building.concrete_volume()
        concrete_rate = self.rate_book[rate_book]['concrete_m3']
        boq_items.append({
            'item': 'Concrete M30',
            'uom': 'm3',
            'qty': concrete_vol,
            'rate': concrete_rate,
            'amount': concrete_vol * concrete_rate,
        })
        total_cost += concrete_vol * concrete_rate
        
        # Reinforcement (tonnes)
        steel_vol = building.steel_weight_tonnes()
        steel_rate = self.rate_book[rate_book]['steel_tonne']
        boq_items.append({
            'item': 'Steel TMT Fe 500',
            'uom': 'tonne',
            'qty': steel_vol,
            'rate': steel_rate,
            'amount': steel_vol * steel_rate,
        })
        total_cost += steel_vol * steel_rate
        
        # Add contingency
        contingency_pct = 12
        contingency_amount = total_cost * contingency_pct / 100
        
        boq_items.append({
            'item': f'Contingency ({contingency_pct}%)',
            'uom': 'lump',
            'qty': 1,
            'rate': contingency_amount,
            'amount': contingency_amount,
        })
        
        # Export
        if format == 'excel':
            return self._export_excel(boq_items, total_cost + contingency_amount)
        elif format == 'csv':
            return self._export_csv(boq_items)
```

**Validation Strategy:** Compare BOQ aggregate cost to construction cost estimate from industry reports for similar building.

**Effort:** 2–3 days  
**Blockers:** Requires rate book data; use CPWD rates (published annually) as fallback.

---

### 11. **Design Review Checklist** — `backend/compliance.py:design_review()`
**Status:** 65% (compliance checks exist; design review logic missing)  
**Current State:** Verifies code compliance; missing pre-submission design review gates

**What's Missing:**
- Pre-submission checklist (drawings, calculations, certifications)
- Sanity checks (height vs. road width, floor area vs. parking, etc.)
- Exception flagging (non-standard setbacks, FSI waiver, height exemption)
- Approver assignment workflow

**Implementation Path:**
```python
# File: backend/compliance.py (EXPAND)
class DesignReviewGate:
    def pre_submission_review(self, building):
        """Check design readiness before submission to authority"""
        checks = {
            'envelope': self._check_envelope(building),
            'parking': self._check_parking(building),
            'setbacks': self._check_setbacks(building),
            'height_road_ratio': self._check_height_road(building),
            'emergency_egress': self._check_egress(building),
            'safety_distance': self._check_safety_distances(building),
        }
        
        passed = all(c['passed'] for c in checks.values())
        exceptions = [c for c in checks.values() if not c['passed']]
        
        return {
            'ready_for_submission': passed,
            'exceptions': exceptions,
            'waiver_applications': [e['suggests_waiver'] for e in exceptions if e.get('suggests_waiver')],
        }
    
    def _check_height_road(self, building):
        """Height should be ≤ 1.5 × (road_width + setback)"""
        height = building.height_m
        road = building.site.road_width
        setback = building.setbacks['front']
        max_height = 1.5 * (road + setback)
        
        return {
            'passed': height <= max_height,
            'actual': height,
            'limit': max_height,
            'shortfall_m': max(0, height - max_height),
            'suggests_waiver': height > max_height,
        }
```

**Validation Strategy:** Run pre-submission review on a V1 building; verify all checks pass or flag appropriate waivers.

**Effort:** 1–2 days  
**Blockers:** None; compliance.py exists.

---

### 12. **S-Curve Reporting** — `backend/finance.py`
**Status:** 80% (S-curve calculation exists; reporting incomplete)  
**Current State:** Calculates cash flow over time; missing Excel export and visualization data

**What's Missing:**
- Monthly S-curve export (month, planned cost, actual cost, cumulative, variance %)
- Cash flow chart data (for frontend charting)
- Cost vs. schedule variance tracking
- Earned value metrics (BCWS, BCWP, ACWP)

**Implementation Path:**
```python
# File: backend/finance.py (EXPAND)
def export_scurve_report(project, format='excel'):
    """Export S-curve as Excel with monthly breakdown and EV metrics"""
    scurve = project.calculate_scurve()
    
    report_data = []
    for month in range(project.duration_months):
        planned = scurve['planned_cumulative'][month]
        actual = scurve['actual_cumulative'][month]
        variance = actual - planned
        variance_pct = (variance / planned * 100) if planned > 0 else 0
        
        report_data.append({
            'month': month + 1,
            'planned_cost': planned,
            'actual_cost': actual,
            'variance': variance,
            'variance_pct': variance_pct,
            'bcws': planned,
            'bcwp': actual * 0.95,  # Placeholder EV
            'acwp': actual,
        })
    
    if format == 'excel':
        return export_to_excel(report_data, 'S-Curve Report')
    elif format == 'json':
        return report_data
```

**Validation Strategy:** Compare S-curve cumulative cost to manual sum of monthly costs; verify variance calculation.

**Effort:** 1 day  
**Blockers:** None; finance.py exists.

---

## PART 3: TIER 2 CORE V4 (4–6 weeks)

### 13. **Approvals Workflow** — `backend/workflow.py` (NEW), `frontend/ApprovalModule.jsx` (NEW)
**Status:** 0% (Multi-user feature; requires new backend and frontend)  
**Requirement:** Enable designers, engineers, cost managers, and project managers to approve designs and calculations in sequence

**Implementation Path:**
```python
# File: backend/workflow.py (NEW)
from enum import Enum
from datetime import datetime

class ApprovalStage(Enum):
    DESIGN = 'Design Review'
    ENGINEERING = 'Engineering Check'
    COST = 'Cost Estimate'
    PROGRAMME = 'Schedule Review'
    FINAL = 'Final Approval'

class ApprovalGate:
    def __init__(self, stage):
        self.stage = stage
        self.required_roles = self._role_for_stage(stage)
        self.approvers = []
        self.status = 'pending'  # pending, approved, rejected
        self.comments = []
        self.created_at = datetime.now()
        self.completed_at = None
    
    def submit_approval(self, approver_id, approved, comment=''):
        """Record approval from one reviewer"""
        self.approvers.append({
            'user_id': approver_id,
            'approved': approved,
            'comment': comment,
            'timestamp': datetime.now(),
        })
        
        # Auto-advance if all reviewers approve
        if approved and len(self.approvers) >= len(self.required_roles):
            self.status = 'approved'
            self.completed_at = datetime.now()
        elif not approved:
            self.status = 'rejected'
            self.completed_at = datetime.now()
    
    def _role_for_stage(self, stage):
        return {
            ApprovalStage.DESIGN: ['architect', 'project_manager'],
            ApprovalStage.ENGINEERING: ['structural_engineer', 'mep_engineer'],
            ApprovalStage.COST: ['cost_manager'],
            ApprovalStage.PROGRAMME: ['project_manager', 'site_manager'],
            ApprovalStage.FINAL: ['client_representative'],
        }[stage]

class WorkflowOrchestrator:
    def __init__(self, project):
        self.project = project
        self.gates = [ApprovalGate(stage) for stage in ApprovalStage]
        self.current_gate_idx = 0
    
    def advance_workflow(self):
        """Move to next gate after current approval"""
        if self.gates[self.current_gate_idx].status == 'approved':
            if self.current_gate_idx < len(self.gates) - 1:
                self.current_gate_idx += 1
                return True, f"Advanced to {self.gates[self.current_gate_idx].stage.value}"
        return False, "Current gate not approved"
    
    def get_pending_approvals(self, user_role):
        """Get gates pending review by this user's role"""
        pending = []
        for gate in self.gates:
            if gate.status == 'pending' and user_role in gate.required_roles:
                pending.append(gate)
        return pending
```

**Frontend Component:**
```jsx
// File: frontend/src/modules/ApprovalModule.jsx (NEW)
import React, { useState } from 'react';
import { Card, Button, TextArea, Chip, Progress } from '@/components/ui';

export function ApprovalModule({ project }) {
  const [approval, setApproval] = useState(null);
  const [comment, setComment] = useState('');
  const [approved, setApproved] = useState(null);

  const handleSubmit = async (approvalId, isApproved) => {
    await fetch(`/api/approvals/${approvalId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ approved: isApproved, comment }),
    });
    // Refresh workflow state
  };

  return (
    <div className="approval-module">
      <h2>Design Approval Workflow</h2>
      <Progress value={project.workflow.progress} max={5} />
      
      {project.workflow.gates.map((gate, idx) => (
        <Card key={idx} className={gate.status}>
          <h3>{gate.stage}</h3>
          <p>Requires: {gate.required_roles.join(', ')}</p>
          
          {gate.status === 'pending' && (
            <>
              <TextArea 
                placeholder="Comments or concerns..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <Button onClick={() => handleSubmit(gate.id, true)}>Approve</Button>
              <Button onClick={() => handleSubmit(gate.id, false)}>Request Changes</Button>
            </>
          )}
          
          {gate.status === 'approved' && <Chip label="Approved" status="success" />}
          {gate.status === 'rejected' && <Chip label="Changes Requested" status="warning" />}
        </Card>
      ))}
    </div>
  );
}
```

**Database Schema:**
```sql
CREATE TABLE approvals (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  stage VARCHAR(50),  -- DESIGN, ENGINEERING, COST, PROGRAMME, FINAL
  status VARCHAR(20), -- pending, approved, rejected
  required_roles TEXT[], -- array of roles
  created_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE TABLE approval_reviews (
  id UUID PRIMARY KEY,
  approval_id UUID REFERENCES approvals(id),
  user_id UUID REFERENCES users(id),
  approved BOOLEAN,
  comment TEXT,
  reviewed_at TIMESTAMP
);
```

**Validation Strategy:** Create multi-user test project; route through all approval gates; verify state transitions.

**Effort:** 4–5 days  
**Blockers:** Requires user authentication and role management (already present in most apps).

---

### 14. **Comments & Annotations** — `backend/comments.py` (NEW), `frontend/CommentThread.jsx` (NEW)
**Status:** 0% (Collaborative feature)  
**Requirement:** Allow users to comment on designs, calculations, and decisions with threaded discussions

**Implementation Path:**
```python
# File: backend/comments.py (NEW)
class Comment:
    def __init__(self, content, author_id, target_type, target_id):
        self.id = uuid.uuid4()
        self.content = content
        self.author_id = author_id
        self.target_type = target_type  # 'design', 'calculation', 'decision'
        self.target_id = target_id
        self.created_at = datetime.now()
        self.replies = []
        self.resolved = False
    
    def add_reply(self, reply_content, author_id):
        reply = Comment(reply_content, author_id, self.target_type, self.target_id)
        self.replies.append(reply)
        return reply
    
    def resolve(self):
        self.resolved = True
        return {'id': self.id, 'status': 'resolved'}

class CommentThread:
    def __init__(self, target_type, target_id):
        self.target_type = target_type
        self.target_id = target_id
        self.comments = []
    
    def add_comment(self, content, author_id):
        comment = Comment(content, author_id, self.target_type, self.target_id)
        self.comments.append(comment)
        return comment
    
    def get_unresolved(self):
        return [c for c in self.comments if not c.resolved]
    
    def get_by_author(self, author_id):
        return [c for c in self.comments if c.author_id == author_id]
```

**Frontend Component:**
```jsx
// File: frontend/src/components/CommentThread.jsx (NEW)
export function CommentThread({ targetType, targetId, user }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');

  const handleAddComment = async () => {
    const response = await fetch('/api/comments', {
      method: 'POST',
      body: JSON.stringify({ content: newComment, targetType, targetId }),
    });
    const comment = await response.json();
    setComments([...comments, comment]);
    setNewComment('');
  };

  return (
    <div className="comment-thread">
      <div className="comments-list">
        {comments.map(comment => (
          <CommentCard key={comment.id} comment={comment} />
        ))}
      </div>
      <div className="new-comment">
        <textarea 
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
        />
        <button onClick={handleAddComment}>Post</button>
      </div>
    </div>
  );
}
```

**Validation Strategy:** Add comments to a design; verify thread creation, replies, and resolution flow.

**Effort:** 2–3 days  
**Blockers:** Requires user authentication.

---

### 15. **Version Control & Branching** — `backend/versions.py` (NEW)
**Status:** 0% (Enables design iteration and comparison)  
**Requirement:** Allow users to create design branches, compare versions, and merge approved designs

**Implementation Path:**
```python
# File: backend/versions.py (NEW)
class DesignBranch:
    def __init__(self, name, parent_version_id, created_by):
        self.id = uuid.uuid4()
        self.name = name
        self.parent_version_id = parent_version_id
        self.created_by = created_by
        self.created_at = datetime.now()
        self.is_merged = False
        self.merged_at = None
    
    def merge_to_parent(self, approval_required=True):
        """Merge this branch back to parent"""
        if approval_required:
            # Check that approvals are complete
            pass
        self.is_merged = True
        self.merged_at = datetime.now()

class VersionControl:
    def __init__(self, project):
        self.project = project
        self.versions = []
        self.branches = []
    
    def create_branch(self, branch_name, from_version_id, created_by):
        """Create a new design branch"""
        branch = DesignBranch(branch_name, from_version_id, created_by)
        self.branches.append(branch)
        return branch
    
    def compare_versions(self, version_a_id, version_b_id):
        """Compare two design versions"""
        version_a = self._get_version(version_a_id)
        version_b = self._get_version(version_b_id)
        
        diff = {
            'height_change': version_b.height - version_a.height,
            'area_change': version_b.gfa - version_a.gfa,
            'cost_change': version_b.cost - version_a.cost,
            'parking_change': len(version_b.parking) - len(version_a.parking),
        }
        return diff
```

**Validation Strategy:** Create alternate designs in branches; compare; merge approved designs.

**Effort:** 3 days  
**Blockers:** None; requires version.py framework.

---

### 16. **Real-time Collaboration** — `backend/sync.py` (NEW), WebSocket integration
**Status:** 0% (Enables concurrent editing)  
**Requirement:** Allow multiple users to edit same project simultaneously with conflict resolution

**Implementation Path:**
```python
# File: backend/sync.py (NEW)
from threading import Lock
from collections import defaultdict

class CollaborativeSync:
    def __init__(self):
        self.active_users = defaultdict(list)  # project_id -> [user_ids]
        self.lock = Lock()
        self.change_log = []
    
    def on_change(self, project_id, user_id, change):
        """Record a change and broadcast to other users"""
        with self.lock:
            self.change_log.append({
                'project_id': project_id,
                'user_id': user_id,
                'change': change,
                'timestamp': datetime.now(),
            })
            
            # Broadcast to all other active users on this project
            other_users = [u for u in self.active_users[project_id] if u != user_id]
            for other_user in other_users:
                self.broadcast_change(other_user, change)
    
    def detect_conflict(self, change_a, change_b):
        """Detect if two concurrent changes conflict"""
        # Simple conflict: both modify same field
        if change_a['field'] == change_b['field']:
            return {
                'conflict': True,
                'resolution': 'last-write-wins',  # Or other strategy
                'winner': change_b,  # Most recent
            }
        return {'conflict': False}
```

**WebSocket Handler:**
```python
# File: backend/websocket_handler.py
class WebSocketHandler:
    def __init__(self):
        self.connections = {}  # user_id -> WebSocket
    
    async def on_change(self, message):
        """Handle real-time change from client"""
        project_id = message['project_id']
        user_id = message['user_id']
        change = message['change']
        
        # Apply change to backend state
        await self.sync.on_change(project_id, user_id, change)
        
        # Broadcast to all connected users
        for conn_user_id, conn in self.connections.items():
            if conn_user_id != user_id:
                await conn.send_json(change)
```

**Validation Strategy:** Open same project in 2 browser tabs; edit simultaneously; verify no data loss or corruption.

**Effort:** 4–5 days  
**Blockers:** Requires WebSocket infrastructure (Socket.io or similar).

---

## PART 4: TIER 3 V5 FOUNDATION (8–12 weeks, partial)

### 17. **IFC Export** — `backend/ifc_export.py` (NEW)
**Status:** 0% (BIM interop; foundational for V5)  
**Requirement:** Export building model as Industry Foundation Classes for import into BIM tools

**Implementation Path:**
```python
# File: backend/ifc_export.py (NEW)
from ifcopenshell import helper

class IFCExporter:
    def __init__(self, building):
        self.ifc_file = ifcopenshell.file(schema='IFC4')
        self.building = building
    
    def export(self, filepath):
        """Export building as IFC file"""
        # Create project structure
        project = self.ifc_file.createIfcProject(
            Name=self.building.name,
            Description=self.building.description,
        )
        
        # Create site and building
        site = self.ifc_file.createIfcSite(Name="Site")
        building = self.ifc_file.createIfcBuilding(
            Name=self.building.name,
            ElevationOfRefLevel=0,
        )
        
        # Add storeys
        for floor_num, floor in enumerate(self.building.levels):
            storey = self.ifc_file.createIfcBuildingStorey(
                Name=f"Level {floor_num}",
                Elevation=floor_num * self.building.floor_height,
            )
            
            # Add elements to storey
            for element in floor.elements:
                self._add_element(storey, element)
        
        self.ifc_file.write(filepath)
    
    def _add_element(self, storey, element):
        """Add a building element (wall, slab, column) to storey"""
        if element.type == 'slab':
            geom = self.ifc_file.createIfcPolyline(
                [self._point(p) for p in element.points]
            )
            slab = self.ifc_file.createIfcSlab(
                Name=f"Slab {element.id}",
                Representation=self._representation(geom),
            )
```

**Validation Strategy:** Export building as IFC; open in open-source BIM viewer (e.g., IFC.js); verify geometry.

**Effort:** 4–5 days  
**Blockers:** Requires ifcopenshell library (free, open-source).

---

### 18. **Revit API Integration** — `backend/revit_sync.py` (NEW)
**Status:** 0% (Requires Revit SDK; advanced BIM feature)  
**Requirement:** Two-way sync with Revit: export geometry, receive BIM changes, update Aptimizer model

**Note:** This is architectural; implementation requires Revit server and user has Revit license.

**Validation Strategy:** (Requires Revit environment; deferred for production use.)

**Effort:** 6–8 days (after V1/V3 complete)  
**Blockers:** Requires Revit license and SDK.

---

### 19. **Digital Twin: IoT Integration** — `backend/iot.py` (NEW)
**Status:** 0% (Requires IoT infrastructure)  
**Requirement:** Connect building sensors (temperature, occupancy, energy, water) to live dashboard

**Implementation Path:**
```python
# File: backend/iot.py (NEW)
class IoTSensor:
    def __init__(self, sensor_id, sensor_type, location):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type  # 'temperature', 'occupancy', 'energy', 'water'
        self.location = location
        self.last_reading = None
        self.last_update = None
    
    def receive_reading(self, value, timestamp):
        """Receive live reading from sensor"""
        self.last_reading = value
        self.last_update = timestamp
        return {'sensor_id': self.sensor_id, 'value': value, 'timestamp': timestamp}

class DigitalTwinDashboard:
    def __init__(self, building):
        self.building = building
        self.sensors = []
    
    def register_sensor(self, sensor):
        self.sensors.append(sensor)
    
    def get_live_status(self):
        """Real-time building status"""
        status = {
            'temperature': self._avg_reading('temperature'),
            'occupancy': self._sum_reading('occupancy'),
            'energy_consumption_kw': self._sum_reading('energy'),
            'water_consumption_lph': self._sum_reading('water'),
            'timestamp': datetime.now(),
        }
        return status
    
    def compare_to_design(self):
        """Compare live performance to design assumptions"""
        live = self.get_live_status()
        design = self.building.design_performance
        
        variance = {
            'temperature_variance': live['temperature'] - design['design_temp'],
            'occupancy_variance_pct': (live['occupancy'] - design['design_occupancy']) / design['design_occupancy'] * 100,
            'energy_variance_pct': (live['energy'] - design['design_energy']) / design['design_energy'] * 100,
        }
        return variance
```

**Validation Strategy:** Connect mock IoT sensors; receive simulated readings; verify dashboard updates.

**Effort:** 5–6 days (after IFC export complete)  
**Blockers:** Requires IoT hardware and MQTT/HTTP bridge.

---

### 20. **AI Co-pilot** — `backend/copilot.py` (NEW)
**Status:** 0% (Aptimizer X feature; requires Claude API integration)  
**Requirement:** Provide design suggestions, code generation, and documentation

**Implementation Path:**
```python
# File: backend/copilot.py (NEW)
import anthropic

class AptimizeAI:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    def suggest_design_improvement(self, building, constraint=None):
        """AI suggests design improvements"""
        prompt = f"""
        Current design:
        - Height: {building.height_m} m
        - FAR: {building.far}
        - Parking: {len(building.parking)} stalls
        - Cost: ₹{building.cost:,.0f}
        
        Constraint: {constraint or 'none'}
        
        Suggest one specific design change to improve the project.
        """
        
        message = self.client.messages.create(
            model="claude-opus-5",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    
    def generate_boq_description(self, item_type, qty, unit):
        """AI generates professional BOQ item descriptions"""
        prompt = f"Write a concise, professional BOQ line description for: {qty} {unit} of {item_type}"
        
        message = self.client.messages.create(
            model="claude-opus-5",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    
    def explain_compliance_check(self, check_name, result):
        """AI explains why a compliance check passed or failed"""
        prompt = f"Explain in one sentence why a building's {check_name} check {'passed' if result else 'failed'}."
        
        message = self.client.messages.create(
            model="claude-opus-5",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
```

**Validation Strategy:** Test suggestion generation on sample buildings; verify suggestions are actionable.

**Effort:** 2–3 days (once backend APIs are stable)  
**Blockers:** Requires Claude API key.

---

## PART 5: IMPLEMENTATION ROADMAP

### Phase 1: Tier 1 Quick Wins (Weeks 1–3)
**Goal:** Push feature completion to 85%+

1. Week 1:
   - Genetic algorithm site packing (3 days)
   - Water demand validation (2 days)
   - CPM float verification (1 day)

2. Week 2:
   - Revit/DWG export (2–3 days)
   - Green rating integration (2–3 days)
   - Parking layout generation (1–2 days)

3. Week 3:
   - Unit mix optimization (1–2 days)
   - Vastu-based unit placement (1–2 days)
   - S-curve reporting (1 day)
   - Embodied carbon baseline (1 day)
   - Design review checklist (1–2 days)
   - BOQ export (2–3 days)

### Phase 2: Tier 2 Core V4 (Weeks 4–9)
**Goal:** Enable multi-user collaboration

4. Week 4–5:
   - Approvals workflow (4–5 days)
   - Comments & annotations (2–3 days)
   - Version control & branching (3 days)

5. Week 6–7:
   - Real-time collaboration sync (4–5 days)
   - Test multi-user scenarios

6. Week 8–9:
   - Polish UI/UX
   - Integrate all features
   - User acceptance testing

### Phase 3: Tier 3 V5 Foundation (Weeks 10–21, partial)
**Goal:** BIM interop and digital twin capability

10. Week 10–12:
    - IFC export (4–5 days)
    - Test with open-source BIM viewer

11. Week 13–15:
    - IoT integration framework (5–6 days)
    - Mock sensor integration

12. Week 16–21:
    - AI co-pilot (2–3 days)
    - Revit API (6–8 days, if Revit available)
    - Documentation and user training

---

## PART 6: TESTING & VALIDATION STRATEGY

### Unit Testing
For each feature, create test file: `backend/tests/test_<module>.py`

```python
# Example: test_genetic_optimizer.py
import pytest
from backend.siteplan.optimize import GeneticOptimizer

def test_genetic_algorithm_converges():
    """Verify GA finds better solution than greedy"""
    greedy_solution = ...
    optimized = GeneticOptimizer(...).optimize(greedy_solution)
    
    assert optimized.fitness > greedy_solution.fitness

def test_water_demand_matches_is1172():
    """Verify water demand matches IS 1172 Table 1"""
    result = water_demand(building_type='residential', occupancy=100)
    expected = 100 * 135  # 13,500 L/day
    assert result['daily_lpd'] == pytest.approx(expected, rel=0.01)
```

### Integration Testing
Create test workflows:
1. Create project → design → engineering → cost & programme → delivery
2. Multi-user approval workflow
3. Version branching and merge

### Validation Against Real Data
For each feature, compare to:
- Published examples (IS code, textbooks)
- Real project data (if available)
- Industry benchmarks

---

## PART 7: PRIORITY SEQUENCING

**Highest Priority (Complete First):**
1. Genetic algorithm (stage 3b completion; unblocks advanced layout)
2. Approvals workflow (enables V4 collaboration)
3. IFC export (foundation for BIM interop)

**High Priority:**
4. Water demand validation
5. Green rating integration
6. Real-time collaboration
7. Version control

**Medium Priority:**
8. Unit mix optimization
9. Parking layout
10. S-curve reporting
11. BOQ export

**Lower Priority (Can delay, nice-to-have first pass):**
12. Revit API integration
13. IoT integration
14. AI co-pilot
15. Vastu-based placement (can be simple rule-based initially)

---

## PART 8: KNOWN BLOCKERS & DEPENDENCIES

| Feature | Blocked By | Unlocks |
|---------|-----------|---------|
| Genetic algorithm | Fitness.py finalization | Advanced site optimization |
| IFC export | None | BIM interop, Revit sync |
| Revit API | Revit license + SDK | Two-way BIM sync |
| IoT integration | None, but needs sensors | Digital twin |
| AI co-pilot | Claude API key | Design assistance |
| Approvals workflow | User auth system | V4 multi-user |
| Real-time collab | WebSocket infrastructure | Live editing |

---

## PART 9: CODE QUALITY CHECKLIST

Before considering a feature "complete":

- [ ] Function docstrings with example usage
- [ ] Unit tests (>80% coverage)
- [ ] Integration test in full workflow
- [ ] Validation against external standard or real data
- [ ] Error handling and user-friendly messages
- [ ] Performance check (no >5s operations on typical data)
- [ ] NBC/IS code references tracked and catalogued
- [ ] Frontend module updated (if user-facing)
- [ ] API endpoint documented (if backend feature)
- [ ] Database schema updated (if data persistence)

---

## PART 10: NEXT IMMEDIATE STEPS

1. **This week:** Implement Genetic Algorithm (stage 3b) → validate with 10 test plots
2. **This week:** Implement Water Demand Validation → compare to IS 1172
3. **Next week:** Implement Approvals Workflow (backend + frontend)
4. **Week 3:** Implement IFC Export → test with open-source viewer
5. **Week 4+:** Continue with remaining Tier 1 features

---

## APPENDIX A: File Structure for New Modules

```
backend/
├── siteplan/
│   ├── optimize.py          [NEW] Genetic algorithm
│   └── __init__.py          [UPDATE] Call optimize.py
├── bim_export.py            [NEW] DWG/Revit export
├── ratings.py               [EXPAND] IGBC/GRIHA scoring
├── sustainability.py        [EXPAND] Embodied carbon
├── planning.py              [EXPAND] Unit mix, parking, Vastu
├── workflow.py              [NEW] Approvals & version control
├── comments.py              [NEW] Threaded comments
├── sync.py                  [NEW] Real-time collaboration
├── ifc_export.py            [NEW] IFC export
├── iot.py                   [NEW] Sensor integration
├── copilot.py               [NEW] AI suggestions
└── tests/
    ├── test_optimize.py     [NEW]
    ├── test_bim_export.py   [NEW]
    ├── test_workflow.py     [NEW]
    └── ...

frontend/
├── src/modules/
│   ├── ApprovalModule.jsx   [NEW]
│   ├── CommentThread.jsx    [NEW]
│   ├── VersionControl.jsx   [NEW]
│   ├── DigitalTwin.jsx      [NEW]
│   └── Copilot.jsx          [NEW]
└── src/components/
    └── RealtimeSync.jsx     [NEW]
```

---

## APPENDIX B: Claude AI Assistance Commands

Once this prompt is loaded, use these commands to guide feature implementation:

```
1. "Implement [Feature Name] following the spec in PART 2 section [N]"
2. "Write unit tests for [Feature Name]"
3. "Integrate [Feature Name] into the approval workflow"
4. "Validate [Feature Name] against [Standard/Real Data]"
5. "Generate frontend module for [Feature Name]"
```

Example:
```
"Implement Genetic Algorithm Site Packing following PART 2 section 1. Start with the FitnessEvaluator class and test on a 1000 m² plot."
```

---

## APPENDIX C: Feature List Completion Status

**Updated:** 2026-09-05

| Version | Category | Feature | Status | Blocker | Priority |
|---------|----------|---------|--------|---------|----------|
| V1 | Site | Plot bounds, constraints | ✓ Built | None | — |
| V1 | Design | Envelope generation | ✓ Built | None | — |
| V2 | Design | Greedy grid packing | ✓ Built | None | — |
| V3 | Design | Genetic refinement | 🔄 Partial | Fitness.py | T1 |
| V1 | Engr | Structural loads (IS 875) | ✓ Built | None | — |
| V3 | Engr | Fire safety (IS 10262) | ✓ Built | None | — |
| V3 | Water | Water demand (IS 1172) | 🔄 Partial | Validation | T1 |
| V3 | Parking | Requirement calc | ✓ Built | None | — |
| V3 | Parking | Layout generation | 🔄 Partial | None | T1 |
| V2 | Cost | S-curve | 🔄 Partial | Excel export | T1 |
| V2 | Cost | NPV/IRR | ✓ Built | None | — |
| V2 | Programme | CPM | 🔄 Partial | Float verify | T1 |
| V3 | Compliance | NBC checks | ✓ Built | None | — |
| V3 | Compliance | Design review | 🔄 Partial | None | T1 |
| V4 | Collab | Approvals | 🚫 Not started | None | T2 |
| V4 | Collab | Comments | 🚫 Not started | None | T2 |
| V4 | Collab | Version control | 🚫 Not started | None | T2 |
| V5 | BIM | DWG export | 🚫 Not started | None | T1 |
| V5 | BIM | IFC export | 🚫 Not started | None | T3 |
| V5 | BIM | Revit sync | 🚫 Not started | Revit SDK | T3 |
| V5 | Twin | IoT integration | 🚫 Not started | Hardware | T3 |
| X | AI | Co-pilot | 🚫 Not started | Claude API | T3 |

**Legend:** ✓ = Built | 🔄 = Partial (in progress) | 🚫 = Not started | T1/T2/T3 = Tier

---

**END OF PROMPT**

---

This comprehensive prompt is now ready for implementation. It provides:
- **Clear specification** for all 28 partial features
- **Code templates** to accelerate development
- **Validation methodology** for each feature
- **Phased implementation** roadmap (Tier 1, 2, 3)
- **Testing strategy** and quality checklist
- **Priority guidance** to maximize impact

You can use this prompt to:
1. Guide AI assistants in feature implementation
2. Track completion status across the team
3. Ensure architectural coherence as features are added
4. Validate features against standards (IS codes, IGBC, etc.)
5. Plan deployment in phases (V1/V3 first, then V4, then V5)

