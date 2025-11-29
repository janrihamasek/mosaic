je třeba v aplikaci mít možnost nastavovat hodnotu active day


- Goal completion (plnění cíle)
ok
- Streak length (počet dnů v řadě)
ok
- Activity distribution (rozložení podle kategorií)
ok
- je důležité, že goal je průměrná hodnota, ze které se spočíta denní cíl, není cílem sama o sobě
- je potřeba definovat proměnnou active_day ve smyslu: if R_d > 50% active_day True else active_day False. defaultně bude hodnota active_day 50%, pak se vymyslí jak s tím dál.
- Rolling averages (7/30denní průměry): nahradit Rolling avereges per category, počítat třicet a sedm dní vyjma dnešek. Nějaký karusel, který umožní listovat ve výsledcích per category.
- Active days ratio (aktivní dny v posledních 30 dnech): aktivní den = active_day True. Nepočítat do výpočtu dnešek.
- Positive vs. negative (poměr kladných a záporných aktivit) změnit na:
	- `positive =` number of entries in `W30` where `value > 0 `.
	- `negative =` number of entries in `W30` where `value = 0`
- Top consistent activities (nejstálejší činnosti): nahradit Top consistent activities per category. Nějaký karusel, který umožní listovat ve výsledcích per category.

Base Adjustments
- `goal` = **average daily reference value** derived from activity frequency, _not_ a direct target to be achieved.  
    → Denote: `G_total = Σ goal_a`, where each `goal_a` is the _average contribution_ of an activity toward the overall daily completion ratio.
- Introduce binary variable:
- active_day(d) = True  if R_d ≥ 0.5
                   False otherwise
- Default threshold = 0.5 (50 %), aligned with frontend "Today progress" bar color change from red → green.
- This flag will serve as the logical basis for streaks, active-day ratios, and future consistency metrics.
---
Rolling Averages per Category (`avg_goal_fulfillment_by_category`)
- **Purpose:** Show average goal completion per category for 7-day and 30-day windows, excluding the current day `T`.
- **Formula:**
	`avg_goal_fulfillment_by_category[c][n] = round((Σ_{i=1}^{n} R_{T−i,c} / n) * 100, 1) where R_{T−i,c} is the daily ratio for category c on day T−i`
- **UI:** Presented in a carousel component allowing horizontal browsing between categories.
---
Active Days Ratio (`active_days_ratio`)
- **Definition:** A day is _active_ if `active_day(d) = True`. 
- **Formula:** 
	`active_days_ratio = round((|{ d ∈ [T−29, T−1] | active_day(d) = True }| / 30) * 100, 1)`
    `Excludes current day T`
- **Interpretation:** Shows how many of the past 30 days were productive (≥ 50 % completion).
---
Positive vs Negative (`positive_vs_negative`)
- **Purpose:** Binary split of all recent entries.
- **Formulae:**
    `positive = number of entries in W30 where value > 0`
    `negative = number of entries in W30 where value = 0`
    `ratio = round(positive / max(negative, 1), 1)`
- **Interpretation:** Ratio of “performed” vs “not performed” entries.
---
Rolling Averages per Category (avg_goal_fulfillment_by_category)
Purpose: Show average goal completion per category for 7-day and 30-day windows, excluding the current day T.
Formula:
	`avg_goal_fulfillment_by_categorycn = round((Σ_{i=1}^{n} R_{T−i,c} / n) * 100, 1)`
    `where R_{T−i,c} is the daily ratio for category c on day T−i`
- UI: Presented in a carousel component allowing horizontal browsing between categories.
---
- Progress:
		1. "Progress", default: "Progress"
		2. na výběr z "Activity"/"Category", default: "Activity"
		3. na výběr z "30 days"/"90 days", default: "30 days"
	 - možnosti:
		 - Progress - Activity - 30 days
			 - vypíše seznam aktivit aktivních v posledních 30 dnech. každý řádek s aktivitou obsahuje její název a Progress bar zobrazující úspěšnost dané aktivity za posledních 30 dní, tu získáme takto:
				 (součet values aktivity aktivní v posledních 30 dnech za posledních 30 dní)/(goal aktivity aktivní v posledních 30 dnech * 30)
		 - Progress - Activity - 90 days
			 - vypíše seznam aktivit aktivních v posledních 90 dnech. každý řádek s aktivitou obsahuje její název a Progress bar zobrazující úspěšnost dané aktivity za posledních 90 dní, tu získáme takto:
				 (součet values aktivity aktivní v posledních 90 dnech za posledních 90 dní)/(goal aktivity aktivní v posledních 90 dnech * 90)
		 - Progress - Category - 30 days
			 - vypíše seznam kategorií aktivit aktivních v posledních 30 dnech. každý řádek s kategorií obsahuje její název a Progress bar zobrazující úspěšnost dané kategorie za posledních 30 dní. tu získáme takto:
				 (součet values aktivit aktivních v posledních 30 dnech v rámci jedné kategorie za posledních 30 dní)/(goals aktivit aktivních v posledních 30 dnech v rámci jedné kategorie * 30)
		 - Progress - Category - 90 days
			 - vypíše seznam kategorií aktivit aktivních v posledních 90 dnech. každý řádek s kategorií obsahuje její název a Progress bar zobrazující úspěšnost dané kategorie za posledních 90 dní. tu získáme takto:
				 (součet values aktivit aktivních v posledních 90 dnech v rámci jedné kategorie za posledních 90 dní)/(goals aktivit aktivních v posledních 90 dnech v rámci jedné kategorie * 90)
- Trend
		1. "Trend", default: "Trend"
		2. na výběr z "Activity"/"Category", default: "Activity"
		3. na výběr z "90 days"/"180 days", default: "90 days"
