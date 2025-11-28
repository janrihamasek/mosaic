# 251127_frontend_T1-daily-loop-ux

Goal:  
Implement the T1 daily loop UX for Today / Entries / Stats tabs (web frontend) according to the “T1 Daily Loop UX Plan” specification, including tab refresh behavior, loading/empty/error states, unified valence/Mood coloring, desktop layout, and minimal mobile behavior.

Context:

- Project: Mosaic – React/TypeScript frontend with Redux store and a dark-mode baseline.
    
- Feature scope: T1 (Daily Tracking core loop) for Today / Entries / Stats tabs only. Backend behavior (including finalize_day) is considered existing and out of scope here.
    
- UX source of truth: The current “T1 Daily Loop UX Plan” (you can assume the user keeps this text synced with the repo; follow the version summarized below).
    

Naming disclaimer:  
All function, selector, endpoint and component names in this prompt are conceptual. Their exact spelling and location in the repository may differ.

- Before creating anything new, always search the repository for an existing symbol with the same purpose and reuse or adapt it.
    
- If a name from this prompt does not exist exactly as written, adapt to the closest matching existing symbol instead of introducing a duplicate.
    

Relevant UX requirements (summary of the spec):

1. Tabs / refresh / stale:
    

- Main “Dashboard” component shows tabs like Today, Entries, Stats (and others).
    
- On first opening Dashboard, the default tab is Today and its data must be loaded.
    
- When switching tabs:
    
    - Today → loadToday() + loadEntries() for “today”, but only if data are stale.
        
    - Entries → loadEntries() for current filter, if stale.
        
    - Stats → loadStats() for current period, if stale.
        
- Staleness logic:
    
    - If a dataset was loaded within the last 60 seconds and no relevant mutation happened since then, skip re-fetch.
        
    - After any write mutation related to entries/activities/finalize day, mark corresponding datasets as stale in the store (e.g. entries.stale = true, today.stale = true, stats.stale = true), so they will be reloaded on next tab visit.
        
- Implement this using a combination of:
    
    - A “Dashboard” container (or equivalent) that watches current tab + stale flags (e.g. via useEffect),
        
    - A listener/middleware that listens to mutation completion actions (e.g. mutationCompleted) and sets stale flags accordingly.
        

2. Loading / empty / error states:
    

- Loading:
    
    - For Today / Entries / Stats tab bodies, show skeleton rows/boxes instead of a bare spinner while fetching data.
        
    - Any “Save”-style button must be disabled during an in-flight save and show a subtle loading state (e.g. “Saving…”).
        
- Empty:
    
    - Today:
        
        - If there are no active activities for the selected day, show a neutral card with:
            
            - text: "No activities for today"
                
            - CTA button: "Add activity" that always navigates to the Activities tab.
                
    - Entries:
        
        - If filtering returns no results, show a simple row/text: "No records for selected filter".
            
    - Stats:
        
        - If there is not enough data, show text: "No statistics available for selected period" plus a short hint that stats will appear after several days of logging.
            
- Error:
    
    - On fetch or mutation error:
        
        - Show a subtle toast/banner in the Dashboard area with: "Failed to load data. Try again."
            
        - Provide an action "Reload" which re-dispatches the appropriate load thunk.
            
    - Background errors (e.g. auto-refresh) must not break the whole dashboard; keep last valid data and show only non-blocking feedback.
        

3. Valence and Mood coloring:
    

- Colors (dark-mode baseline, used consistently across app where valence is visualized):
    
    - positiveColor = #22aa5e
        
    - negativeColor = #b74444
        
    - neutralColor = #858486
        
    - moodColor = #6b7280
        
- Valence mapping:
    
    - positive → use positiveColor as a subtle “success” tone (e.g. light cell background or left border).
        
    - negative → use negativeColor as a subtle “danger” tone.
        
    - neutral → use neutralColor or a neutral background, but any place that visually differentiates valence must be based on these three colors.
        
- Where:
    
    - Entries tab: the value/score column should visually reflect valence using positiveColor / negativeColor / neutralColor (e.g. background, border).
        
    - Today tab: if there is a visible value column, it should use the same color mapping as Entries for valence.
        
- Mood as a specific activity:
    
    - Activity “Mood” has valence = neutral and does not affect goal/completion.
        
    - In Entries:
        
        - Mood appears as a normal activity row, but its value/border/icon uses moodColor (instead of neutralColor), so it is visually distinguishable.
            
    - In Stats:
        
        - Mood is currently not visualized at all (no separate column or chart).
            
    - In Today:
        
        - Current Mood value for the selected day is shown in the header as text "Mood: 3/5" (or equivalent), styled with moodColor.
            
- Implementation detail:
    
    - Use existing helpers from frontend/styles/common.js (or equivalent) to generate className based on valence and for Mood, instead of introducing new ad-hoc inline styles.
        

4. Desktop layout consistency (Today / Entries / Stats):
    

- Columns and alignment:
    
    - Today vs Entries should share:
        
        - Column order: Activity | Value | Valence/Mood | Note | Actions
            
        - Alignment: labels left, numeric values right, icons centered.
            
- Column widths:
    
    - Set minimum widths so that header labels do not wrap into multiple lines at typical desktop widths.
        
    - If the table is wider than the viewport, allow horizontal scrolling inside the tab body only (not the whole page).
        
- Inline editing:
    
    - Today uses inline editing:
        
        - Click on a cell → show an input.
            
        - On blur or Enter: save changes (or revert to original on cancel).
            
        - Esc discards changes.
            
    - Notes:
        
        - Use a short inline input in the row (no popover) to enter/edit the note without significantly increasing row height.
            
- Day header:
    
    - Above the Today table (in the Today tab), show:
        
        - The selected date.
            
        - The current Mood value text "Mood: 3/5" (or equivalent) styled with moodColor.
            
    - finalize_day runs automatically in the backend at the end of the day (adding missing zero entries for activities with value 0) and should not have any explicit button or badge in the web UI.
        

5. Mobile behavior (minimal T1 scope):
    

- For viewport width < ~768px:
    
    - Today:
        
        - Replace the pure table layout with a stacked “card” representation:
            
            - Row 1: activity name.
                
            - Row 2: value + valence (colorized by valence colors).
                
            - Row 3: mood/note (if present).
                
    - Entries:
        
        - Keep a table, allow horizontal scrolling with the first column (activity name) fixed.
            
        - Do not switch Entries to cards.
            
    - Stats:
        
        - Charts must be responsive (width 100%), no horizontal scroll.
            
- Interactions:
    
    - Buttons such as Save should be full-width on mobile for easy tapping.
        
    - On mobile, primary focus is quick daily input; configuration and secondary actions are hidden:
        
        - Less frequently used actions (Entries filters, export, Admin, other secondary tabs) go behind a menu.
            
        - Main visible tabs in mobile navigation are Today, Stats, and Activities; all other tabs are accessible only via the secondary/menu navigation.
            

Tasks:

1. Analyze existing Dashboard, Today, Entries, Stats components and Redux store slices/selectors:
    
    - Identify current tab-switch behavior, load thunks/selectors, and any existing stale or loading flags.
        
    - Identify where valence and Mood are already present in the data model (entries, activities) and how they are currently rendered.
        
2. Implement tab refresh and stale logic:
    
    - Introduce or adapt stale flags for today, entries, stats in the store.
        
    - Implement a listener/middleware that:
        
        - Reacts to mutation completion actions for entries/activities/finalize day.
            
        - Sets appropriate stale flags to true.
            
    - In the Dashboard container, use a useEffect (or equivalent) on the active tab + stale flags to:
        
        - Load data on initial mount and when a tab becomes active with stale data.
            
        - Apply the 60-second freshness window to skip redundant fetches.
            
3. Implement loading / empty / error states:
    
    - Add skeleton UIs for Today, Entries, Stats tab bodies when loading.
        
    - Ensure Save-like actions disable their buttons and show “Saving…” during in-flight writes.
        
    - Implement empty state UIs and copy exactly as specified:
        
        - Today: "No activities for today" + "Add activity" (navigate to Activities).
            
        - Entries: "No records for selected filter".
            
        - Stats: "No statistics available for selected period" + hint.
            
    - Implement non-blocking error handling:
        
        - Toast/banner with "Failed to load data. Try again." and a "Reload" action that re-dispatches the relevant load thunk.
            
        - Preserve last valid data when background refresh fails.
            
4. Implement unified valence/Mood coloring:
    
    - In frontend/styles/common.js (or equivalent), define or adapt helpers to map valence to:
        
        - positiveColor = #22aa5e
            
        - negativeColor = #b74444
            
        - neutralColor = #858486
            
    - Add a variant for Mood using moodColor = #6b7280.
        
    - Apply these helpers in:
        
        - Entries value/score column (and any similar valence visuals),
            
        - Today value column (if rendered),
            
        - Mood row in Entries,
            
        - Mood text in Today header.
            
    - Verify that the color usage is consistent in dark mode and passes basic contrast expectations.
        
5. Enforce desktop layout consistency:
    
    - Align Today and Entries tables to the shared column order and alignment.
        
    - Adjust column widths and horizontal scroll behavior as specified.
        
    - Implement inline editing in Today (including notes) with the described Enter/Esc behavior.
        
    - Implement the Today header with date + Mood text and remove any leftover finalize-day UI elements if present.
        
6. Implement mobile behavior:
    
    - Add responsive breakpoints around ~768px.
        
    - For Today:
        
        - Implement the stacked card representation for each activity row with the specified three lines.
            
    - For Entries:
        
        - Implement horizontal scroll with sticky first column for activity name.
            
    - For Stats:
        
        - Ensure charts are full-width and do not require horizontal scrolling.
            
    - Adjust navigation on mobile:
        
        - Make only Today, Stats, Activities visible as main tabs.
            
        - Move other tabs into a secondary menu.
            
    - Ensure Save-like buttons are full-width on small screens.
        
7. Clean up and verify:
    
    - Remove any obsolete loading/empty/error UI code that conflicts with the new behavior.
        
    - Ensure there are no leftover references to finalize-day buttons or Closed/Open badges.
        
    - Add or update unit/integration tests where appropriate (e.g. for listener/stale behavior and basic rendering of new states).
        
    - Run the app and manually verify the T1 daily loop on desktop and mobile widths.
        

Output:

- A list of all modified/created frontend files (paths).
    
- For each affected component/store module:
    
    - A short description of changes and how they implement the UX requirements above.
        
- A brief checklist showing which UX requirements (1–5) are covered and how (one or two lines per requirement).