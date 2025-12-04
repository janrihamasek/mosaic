dev
	FRONTEND_API_URL=https://10.0.1.31:5000 FRONTEND_API_KEY=dev-api-key FRONTEND_BACKEND_LABEL="Dev API" docker compose up --build

prod
	 FRONTEND_API_URL=https://10.0.1.31:5001 FRONTEND_API_KEY=prod-api-key FRONTEND_BACKEND_LABEL="Prod API" docker compose up --build


Rebuild dev backendu, upgrade databáze, testy

docker compose up -d --build mosaic_backend_dev

docker compose exec mosaic_backend_dev flask db upgrade
docker compose exec mosaic_backend_dev pytest | tee backend/pytest_output.txt

Snadný způsob, jak zjistit, co Docker právě dělá:

- docker ps – ukáže běžící kontejnery (ID, image, příkaz, jak dlouho běží, otevřené porty). Pro stack Mosaic používej raději docker compose ps, protože filtruje na kontejnery z aktuálního docker-compose.yml.
- docker compose ps – v adresáři projektu (/home/jan/Dokumenty/code/mosaic) zobrazí stav všech služeb (running, exited, připojené porty). Přepínač --services --status vytiskne jen názvy a stavy.
- docker compose logs -f <služba> – sleduje logy konkrétní služby v reálném čase, takže vidíš, zda něco právě provádí.
- docker stats – živé statistiky (CPU, paměť), dobré pro zjištění, zda se kontejnery nepřetěžují.
- docker compose top – zobrazí procesy běžící uvnitř kontejnerů.

docker compose exec postgres psql -U mosaic -d postgres
\c mosaic_prod
UPDATE users SET is_admin = TRUE WHERE username = 'jan';
SELECT id, username, is_admin FROM users WHERE username = 'jan';
\q
