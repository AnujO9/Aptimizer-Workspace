#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Continue Aptimizer after V1 (Auth/RBAC, Projects, Plot, Apartment Planning, Calculations, Parking,
  Quantities, BOQ, Cost, Utilities, Compliance, Reports — already tested, must stay untouched).
  Build the two PRD backlog items: (1) GIS & Site Intelligence V2 reading the existing plot polygon —
  Overpass feature detection, Open-Elevation terrain/slope, flood risk, wind, sun path, accessibility,
  site suitability score, buildability flags, AI site analysis via the Emergent Universal LLM key, and
  GIS↔Plot sync; (2) 3D interactive UI with react-three-fiber reading the same MongoDB project document —
  terrain, tower massing, detailed floor slabs, 3D floor plan, floor slider, section cut, layer toggles,
  compliance highlighting, selection side panel, instanced meshes and a simple 2D fallback.

backend:
  - task: "GIS analysis endpoint (Overpass + Open-Elevation + flood/wind/sun/accessibility/suitability/buildability)"
    implemented: true
    working: true
    file: "backend/gis.py, backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "POST /api/projects/{id}/gis/analyse persists results at project.gis and logs gis.analysed. GET /api/projects/{id}/gis returns stored result + stale flag from polygon signature. 11/11 tests in backend/tests/gis_test.py pass; live run on the default Bengaluru plot returned 120 buildings, 120 roads, slope 3.04%, flood high, accessibility 94, suitability 74.6 in ~12s. Overpass has 3 mirror fallbacks; graceful degradation if a source fails."

  - task: "AI site analysis via Claude Sonnet 4.6 (Emergent Universal Key)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "POST /api/projects/{id}/gis/ai-summary builds context from suitability/buildability/terrain/flood/access/wind/sun and stores markdown at project.gis.ai_summary. Returns 400 before analysis is run, 503 without a key. Verified live output quoting real numbers."

  - task: "V1 endpoints regression"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Only additive changes: gis routes + 'gis' added to the PUT allow-list. backend_test.py 32/32 still pass. Note: a duplicated block at the end of server.py (pre-existing) was removed so the module imports cleanly."

frontend:
  - task: "GIS Intelligence module UI"
    implemented: true
    working: true
    file: "frontend/src/modules/GisModule.jsx, components/GisMap.jsx, components/SiteDiagrams.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Radius input + run/re-run, stale banner, source status line, Leaflet map with per-layer toggles over satellite/OSM, suitability breakdown bars, buildability flags, elevation profile chart, flood panel, sun-path polar diagram with time slider, wind rose, accessibility notes, AI summary render. Verified by screenshot; needs testing_agent interaction depth."

  - task: "3D visualisation module"
    implemented: true
    working: true
    file: "frontend/src/modules/ThreeDModule.jsx, frontend/src/lib/scene.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: true
        -agent: "main"
        -comment: "Site/massing/floor-plan views, GIS terrain heightfield, plot outline + road edge + compass, sun slider + season, instanced buildings/floor slabs/parking slots, tower click-to-isolate, detailed slabs coloured by unit type, 3D floor plan with walls/door gaps/windows, floor slider, section cut, walk mode, layer toggles, violation highlighting, selection side panel, simple 2D fallback. Screenshots confirm all three views render."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 2
  run_ui: true

test_plan:
  current_focus:
    - "GIS Intelligence module UI"
    - "3D visualisation module"
    - "GIS analysis endpoint"
    - "AI site analysis"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "V2 complete. Backend: 43/43 pytest tests pass (32 V1 + 11 new GIS). Please verify the two new frontend modules end to end (nav-module-gis, nav-module-3d) and confirm no V1 regression. GIS analysis takes ~10-20s (external APIs) so allow generous waits. AI summary takes ~15-30s."
