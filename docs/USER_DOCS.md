# Mosaic User Documentation

## 1. Overview

Mosaic helps you track daily habits, activities, and goals.
It lets you record what you did each day, add notes, and view your progress over time through simple visual summaries.

**Main Sections:**

* **Today:** Record daily results.
* **Activities:** Manage tracked habits or goals.
* **Stats:** Review your progress and consistency.
* **Entries:** View or export historical data.

---

## 2. Getting Started

1. Open the Mosaic dashboard and register a new account.
2. Log in with your credentials.
3. You will see four main tabs — *Today*, *Activities*, *Stats*, *Entries*.

**Tip:** Your session remains active; if inactive too long, log in again.

---

## 3. Activities

* Go to **Activities → Create Activity**.
* Define name, category, and goal (e.g., “Run”, goal = 1 × per day).
* You can deactivate activities anytime (they stay stored but hidden).
* Hover shows the category; clicking allows editing or deletion.

---

## 4. Today

* Each row represents an activity for the current day.
* Click the value (0–5) to record how well the goal was met.

  * Value = 0 → not done
  * Value = 5 → fully completed
* Notes can be added up to 100 characters.
* **Saving:**

  * Value is saved immediately on click.
  * Note is saved on Enter or after 5 seconds of inactivity.
* Toasts confirm auto-saves and errors.

---

## 5. Statistics

* Displays aggregated 30-day insights.
* Widgets include:

  * Goal completion (%)
  * Active streaks
  * Distribution by activity and polarity
  * Consistency indicators
* Refresh button updates data manually.
* Over 100 % completion is shown in orange to indicate over-achievement.

---

## 6. Entries

* Shows full historical records.
* Supports pagination, sorting, and filtering.
* Rows with values > 0 are highlighted in green.
* You can export data via the **Export** button (CSV or JSON).

---

## 7. Import and Export

**Import CSV:**

* Accessible from the Entries tab.
* File must include columns: `date`, `activity`, `value`, `note`.
* Invalid or duplicate rows are skipped; a summary is shown.

**Export CSV/JSON:**

* Generates downloadable file of all your entries and activities.
* Useful for personal analysis or backup.

---

## 8. Data Backup

Mosaic automatically creates periodic backups of your data (JSON + CSV).
You can view, download, enable, or disable backups in **Settings → Backups**.
Backups are stored locally in your user directory or in configured cloud storage (future option).

---

## 9. Account and Settings

* Manage profile name, password, and session from **User Menu → Profile**.
* Logout anytime; your data remains stored.
* Upcoming: profile photo, language options, and data import preferences.

---

## 10. Tips & Examples

* Combine positive and negative habits (e.g., “Exercise” vs “No smoking”).
* Use notes for quick reflections (e.g., mood or reason for failure).
* Review your Stats weekly to adjust goals.
* Example CSV:

```
date,activity,value,note
2025-11-02,Running,5,Good weather
2025-11-02,Reading,3,Slightly tired
```

---

## 11. Troubleshooting

* **Data not saving:** check connection or re-login.
* **CSV import fails:** verify header names and date format (YYYY-MM-DD).
* **Streak missing:** activity may have been deactivated or value = 0.
* **Account locked:** wait 5 minutes (rate limit protection).

---

## 12. Contact / Feedback

For questions or feature requests, open an issue on the Mosaic GitHub repository or contact support at `support@mosaic.app`.

---

Chceš, abych to převedl do formátu pro Codex prompt (tj. úkol typu „vytvoř USER_DOCS.md podle této struktury“)?
