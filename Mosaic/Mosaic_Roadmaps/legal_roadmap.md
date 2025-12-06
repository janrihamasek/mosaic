- [ ] I. Technická připravenost – v rozsahu „self-host alpha“, ne Play:
- HTTPS-only, žádné hardcoded secrets, základní healthcheck `/healthz`.
- Android App Bundle (.aab), Target API level 34, Privacy Manifest, HTTPS-only, žádné hardcoded keys.
- Subscription Billing (Google Play Billing Library), ladění výkonu a stability.

- [ ] II. Právní požadavky (GDPR + Google Play Policy):
- Privacy Policy v minimální verzi, Terms of Use pro testery, základní soulad s Play zásadami.
- Privacy Policy + Terms of Use už ne jen „pro testery“, ale pro veřejnost.

- [ ] III. Produktová péče:
- definovaný základní cyklus verzí (např. minor release 1× měsíčně), bugfix proces, support kanál.
- roadmapa pro další datové zdroje a funkce, řízení dluhu (UX, performance).

- [ ] IV. Právní forma:
- rozhodnutí, v jaké právní formě můžeš přijímat platby (OSVČ / s.r.o. apod.) a co to pro tebe znamená.

- [ ] V. Licence, autorská práva:
- případné smluvní/licenční otázky kolem integrace třetích stran (pokud vzniknou).
- minimálně jméno/logo, licence k použitému obsahu, základní ochrana značky, pokud dává smysl.

- [ ] VI. Uživatelská data, hosting:
- Lokální / self-host backend, zálohy DB, základní monitoring.
- vybraný hosting (VPS / cloud), nastavené logování, monitoring, manuální proces záloh a obnovy.
- řešení objemu dat, retence, anonymizace, Data Retention Policy v praxi.