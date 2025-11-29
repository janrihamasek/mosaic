# Daily Log – 2024-11-14

- Date: 2024-11-14
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 14_11_mosaic.md

## Notes (raw import)

--- code freeze ---
- **Zastav růst a stabilizuj**  
    Udělej krátkou fázi „freeze“ (týden, dva), kdy jen opravuješ, měříš a čistíš.  
    Žádné nové featury.
    
- **Zaveď mapu závislostí**  
    Může to být obyčejný text nebo graf: co volá co, kde jsou Redux slice ↔ API ↔ DB vazby.  
    Pomůže to odhalit, co už je příliš provázané.
    
- **Vymez vrstvy**  
    Přesně popiš, které části systému se smějí dotýkat jiných.  
    Např.: „Frontend volá jen API; API pracuje jen přes service vrstvy; service přistupují k DB.“

251114_architecture_dependency_map
Goal: Create docs/architecture/dependency-map.md summarizing all dependency flows across frontend, backend, Redux, services, and DB.

**Dependency Map**

- Added docs/architecture/dependency-map.md (line 1) detailing every component→slice→thunk→apiClient flow, including how auth/offline helpers and the admin panels call into the Flask endpoints.
- Captured the cross-slice refresh chains plus backend controller→service→model mappings alongside cache architecture and the explicit invalidation table so you can reason about dependencies end to end (docs/architecture/dependency-map.md (line 32), docs/architecture/dependency-map.md (line 44), docs/architecture/dependency-map.md (line 66)).
- Documented the specialised NightMotion stream proxy, BackupManager scheduler, and metrics/health instrumentation flows for quick reference when touching those systems (docs/architecture/dependency-map.md (line 80), docs/architecture/dependency-map.md (line 88), docs/architecture/dependency-map.md (line 96)).

251114_architecture_dependency_graph
Goal: Create docs/architecture/dependency-graph.md containing system-wide dependency diagrams.  

- Added docs/architecture/dependency-graph.md (line 1) with two Mermaid diagrams: a global end-to-end dependency flow (React components → Redux slices/thunks → apiClient → Flask controllers → services/models/DB) plus data-flow clusters for Today/Entries/Stats and Admin/Backup/Metrics/NightMotion, including highlighted high-coupling nodes.
- Documented feedback loops, cache invalidation paths, and why apiClient, controllers, entriesSlice, and BackupManager demand extra care when modifying dependencies (docs/architecture/dependency-graph.md (line 53), docs/architecture/dependency-graph.md (line 108)).

251114_architecture_redux_flow
Goal: Create docs/architecture/redux-flow.md describing Redux slice interactions and API usage.

- Added docs/architecture/redux-flow.md (line 1) which catalogs every Redux slice (auth, activities, entries/today/stats, backup, admin, nightMotion), detailing each thunk, its HTTP endpoint(s), and all downstream cascades or implicit dependencies so you can trace flows like createActivity → refresh Today/Stats or saveDirtyTodayRows → refresh all data.
- Documented cross-slice behavior explicitly (e.g., activity mutations triggering Today/Entries reloads, backup actions reloading scheduler state, Dashboard bootstraps reacting to auth changes) to make bidirectional or implicit dependencies easy to spot (docs/architecture/redux-flow.md (line 63), docs/architecture/redux-flow.md (line 109)).

251114_architecture_backend_call_tree
Goal: Create docs/architecture/backend-call-tree.md showing call trees for all Flask endpoints.

- Added docs/architecture/backend-call-tree.md (line 1), documenting every Flask endpoint’s call tree: request hooks, validation, rate-limit checks, DB/service operations, cache invalidations, and response steps for auth, activities, entries/today/stats, backups, exports, ingest, logging, and metrics.
- Included focused sections for BackupManager internals, NightMotion stream proxy, wearable ETL, and shared helpers (cache scopes, rate limiting) so contributors can trace end-to-end backend behavior quickly.

251114_architecture_dependency_matrix
Goal: Create docs/architecture/dependency-matrix.md containing a cross-dependency matrix for Mosaic.

- Added docs/architecture/dependency-matrix.md (line 1), documenting a cross-layer matrix that maps React components, Redux slices/thunks, apiClient, Flask endpoints, services, models, cache, metrics, NightMotion, and BackupManager to their direct dependencies, with hotspot notes and guidance on acceptable exceptions.
- Added cross-links in docs/architecture/dependency-map.md (line 3) so it now points readers to the graph, Redux flow, backend call tree, and dependency matrix companion docs.
- Updated docs/architecture/dependency-graph.md (line 3) to mention the rest of the architecture doc set for a consistent navigation path.
- Extended docs/architecture/dependency-matrix.md (line 3) with references back to the map, graph, and Redux flow docs for a cohesive set of architecture references.

251114_architecture_layering_rules
Goal: Create docs/architecture/layering-rules.md defining Mosaic’s architectural layers and allowed dependency directions.

- Added docs/architecture/layering-rules.md (line 1), defining Mosaic’s UI, Redux, API, controller, service, model, and infrastructure layers, along with explicit allowed dependency directions, forbidden shortcuts (e.g., no direct fetch in components, no slice cross-imports, services returning plain data), and real-world examples of compliant vs violating patterns.

251114_architecture_layering_checklist
Goal: Create docs/architecture/layering-checklist.md with a concise PR review checklist enforcing layer boundaries.

- Added docs/architecture/layering-checklist.md (line 1), a 15-point PR review checklist reinforcing the layering rules (no direct fetch/storage in components, slices stay isolated, thunks go through apiClient, controllers delegate to services, services avoid Flask objects, models stay pure, cycles forbidden, exceptions documented, etc.), giving reviewers a quick reference for spotting violations.

251114_architecture_layering_refactor_plan
Goal: Create docs/architecture/layering-refactor-plan.md outlining concrete steps to fix layer violations in Mosaic.

- Added docs/architecture/layering-refactor-plan.md (line 1), outlining current layering violations (cross-slice orchestration, controllers handling SQL, cache scatter, etc.), the desired target architecture, and a phased refactor roadmap (documentation/CI, Redux mutation services, backend service extraction, cache/infra modules, NightMotion/Backup isolation, and final testing considerations).

251114_architecture_repo_structure
Goal: Create docs/architecture/repo-structure.md proposing a clean directory structure for Mosaic respecting the defined layers.  

- Added docs/architecture/repo-structure.md (line 1), proposing an explicit directory tree for backend (controllers, services, repositories, models, infra, tests), frontend (components, pages, store/slices/listeners, services/api/mutations, utils), and docs so the layering rules map cleanly onto the filesystem. Document includes mapping notes and benefits for CI and refactors.

251114_architecture_guardrails
Goal: Create docs/architecture/guardrails.md describing linting and tooling rules that enforce layer boundaries.  

- Added docs/architecture/guardrails.md (line 1), capturing a dependency-direction table and tooling strategy: ESLint boundary/import rules to prevent components and slices from reaching into restricted modules, madge for cycle detection, plus flake8/custom Python checks ensuring controllers don’t import repositories/models, services stay Flask-free, and cache access lives in services/infra. Includes CI integration notes.

251114_repo_extract_backend
Goal: Move the entire backend out of mosaic_prototype/backend into a new top-level backend directory.

Moved mosaic_prototype/backend to a new top-level backend/ directory via git mv, keeping the existing structure (manage.py, migrations, tests, etc.) untouched but now rooted at backend/…. Updated all tooling references so builds keep working: Dockerfile.backend now copies from backend/, docker-compose.yml mounts ./backend:/app for the dev service, and README setup steps tell contributors to cd backend. Adjusted docs (docs/architecture/dependency-map.md, docs/architecture/repo-structure.md) to mention the new path so future work references the right location.

Tests not run (structural move only); recommend running the backend pytest suite or docker compose up mosaic_backend_dev to verify the relocated paths behave as expected.

251114_repo_extract_frontend
repo_extract_real_frontend
Goal: Remove symlink frontend from mosaic.

- frontend/ symlink removed (git rm frontend), and the full codebase previously under mosaic_prototype/frontend/ was moved into the new top-level frontend/ directory via git mv. Every file—from configs and scripts to sources and build artifacts—is now located directly under frontend/, so tools like the Docker build can access frontend/Caddyfile (and the rest) without following a symlink.
- mosaic_prototype/ now contains only database/ and docs/; there are no remaining references to mosaic_prototype/frontend. frontend/ is the single authoritative UI directory going forward.

 251114_repo_extract_docs
Goal: Unify documentation into a single top-level docs directory.

- Merged all documentation into the top-level docs/ directory: every file and subfolder from mosaic_prototype/docs/ (API docs, deployment guides, changelog, frontend page specs, etc.) was moved via git mv into docs/, so the history is preserved.
- Removed the now-empty mosaic_prototype/docs folder; there are no remaining references to the old path (rg "mosaic_prototype/docs" → none).
- Existing docs/architecture/... files remain untouched; the consolidated docs/ now contains architecture docs, changelog, frontend specs, and operational guides in one place, ready for updated links/organization as needed.

mosaic_prototype/database/ je součást backendu → a musí být zahrnuto do restrukturalizace.  
V původních promtech jsem to nezmínil, ale do čisté struktury patří jednoznačně pod backend/.
To znamená:
mosaic_prototype/database/ → přesunout do backend/database/
upravit všechny relativní importy v backendu, které na ni odkazují
zajistit, že Docker Compose, testy, CLI, migrations ji dál najdou
že nic nezůstane v mosaic_prototype/
Přesunul jsem mosaic_prototype/database/ do backend/database/ pomocí git mv, takže init a schema skripty jsou součástí backendu. docker-compose.yml teď mountuje ./backend/database/init-mosaic.sql, aby Postgres inicializace fungovala. V repu už nejsou žádné odkazy na mosaic_prototype/database, takže vše potřebné běží z nové cesty.

251114_repo_fix_import_paths
Goal: Ensure all Python and JavaScript/TypeScript import paths remain valid after directory restructuring.
Context: Moving backend and frontend will break relative imports. Codex must automatically scan and fix them.
Tasks: 1. Scan backend for relative imports referencing mosaic_prototype.* and update to backend.* or local-relative paths; 2. Scan frontend for absolute and relative imports that assumed old directory layout; 3. Update internal service, slice, util, and component imports; 4. Validate tsconfig baseUrl mappings if used; 5. Run static analysis to ensure no missing modules.
Output: Fully functioning backend and frontend codebases with corrected imports and no broken paths.
251114_repo_gitignore_cleanup
Goal: Add proper ignore rules to clean the repo from Android/Node caches and build artifacts.
Context: mobile/android includes .gradle, .idea, build artifacts; multiple builds exist; node_modules and dist must stay ignored.
Tasks: 1. Update .gitignore with patterns: `mobile/android/.gradle/, obile/android/.idea/, **/build/, **/dist/, **/node_modules/`; 2. Remove tracked files that match these patterns; 3. Ensure cleanup does not remove required source code; 4. Verify frontend and mobile builds still run.
Output: Clean .gitignore, removed cached build files, and validated that builds run normally.
251114_repo_ci_update
Goal: Update all CI workflows to use unified backend, frontend, and docs paths.
Context: CI scripts reference mosaic_prototype paths that will no longer exist.
Tasks: 1. Update GitHub Actions workflows under .github/workflows to reference backend/, frontend/, and docs/; 2. Update test commands, working-directory settings, and Docker Compose paths; 3. Ensure staging build uses new paths; 4. Validate that scripts/run_pytest.sh still targets backend.    
Output: Updated CI workflow files ensuring successful backend/frontend test and build pipelines.
- Updated .gitignore to cover all requested caches/build artifacts (**/node_modules/, **/dist/, **/build/, Android .gradle/.idea, etc.) while keeping the existing mobile/android/ ignore so unrelated source doesn’t show up in git status. Removed the previously committed frontend/build/ bundle so builds are regenerated per environment.
- Moved the legacy database bootstrap scripts into backend/database/ and pointed Docker Compose’s Postgres init volume at the new location, so backend migrations/tests continue to find init-mosaic.sql.
- Refreshed every GitHub Actions workflow to use the new top-level paths: backend/ for Python jobs and frontend/ for Node jobs. Cache paths, working directories, artifact uploads, and path filters now all target the unified layout, ensuring CI no longer references mosaic_prototype/....
- Verified import/path health by running npm run lint -- --max-warnings=0 inside frontend/ (passes) and python3 -m compileall backend to ensure Python modules compile cleanly with the relocated directories.
Repo is now free of the old mosaic_prototype references in builds, has clean ignore rules, and CI/test tooling points to the single-source backend/ and frontend/ directories.

251114_repo_final_consistency_check
Goal: Confirm repository integrity after restructuring.
Context: After all moves Codex must validate the working state.
Tasks: 1. Run backend unit tests; 2. Build frontend; 3. Run lint and type checks; 4. Verify Docker Compose startup; 5. Confirm scripts/generate_repo_tree.py still generates correct tree; 6. Output summary of successful consistency.
Output:  A validated, clean, unified repository structure ready for further development.
Níže máš finální Codex prompt ve **správném projektu formátu**.  
Je navržen tak, aby:

- převedl všechny modely v `backend/models.py` na **typed SQLAlchemy 2.x**
    
- nepřepsal databázi ani migrace
    
- zachoval původní sloupce i chování
    
- odstranil Pylance noise způsobený dynamickými typy
    
- neprováděl žádné commit akce (dle tvých pravidel)
    

Podle tvých instrukcí je to **jediný blok bez markdownu**, připravený k vložení do Codexu.

251114_backend_sqlalchemy2_typed_models

Goal:  
Migrate all SQLAlchemy models in backend/models.py to typed SQLAlchemy 2.x syntax using Mapped[] and mapped_column while preserving database schema and behavior.

Context:  
The backend uses declarative SQLAlchemy models with dynamic attributes that cause extensive Pylance noise. Migrating to the typed SQLAlchemy 2.0 ORM eliminates unknown attribute warnings. No database or migration changes should occur; only Python type-level refactoring.

Tasks:  
Convert each model class to SQLAlchemy 2.0 typed style; add type hints using Mapped[...] for all columns and relationships; replace Column(...) with mapped_column(...); keep table names, constraints, indexes, and relationships identical; ensure imports use sqlalchemy.orm.Mapped and mapped_column; preserve existing hybrid properties, methods, and backrefs; do not modify Alembic migrations; run through all relationship definitions and add proper type hints; ensure models still import correctly in the app.

Output:  
Updated backend/models.py rewritten in typed SQLAlchemy 2.x style with Mapped[] and mapped_column, preserving schema and logic, eliminating Pylance dynamic attribute issues.