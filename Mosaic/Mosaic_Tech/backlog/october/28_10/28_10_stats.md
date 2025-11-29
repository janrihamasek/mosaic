# Daily Log – 2024-10-28

- Date: 2024-10-28
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 28_10_stats.md

## Notes (raw import)

1. Na kartě Today mezi tlačítky "Next day" a "Save all changes" umístit progress bar ukazující "Today progress". Today progress získáme takto: today progress = (the sum of executed activities values(date)) / (the sum of avg_goal_per_day of active activities(date)). Při listovaní pomocí tlačítek "Previous day" a "Next day" se musí Today progress dynamicky měnit podle aktuálního dne.

2. nová karta Stats
	- na kartě Stats budou na řádku tři selecty, kterými se nastaví požadované statistiky:
		1. zatím jen "Progress", default: "Progress"
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
	- design progress baru sjednotit s progress barem použitým na kartě Today
 
