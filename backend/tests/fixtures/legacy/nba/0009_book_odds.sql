-- Momios de varias casas de la API por pierna (PRICE_BOOKMAKERS, p. ej. Bet365 y 1xBet):
-- {"Bet365": 1.83, "1xBet": 1.87}. `odd` / `bookmaker` siguen siendo los de BOOKMAKER, con los que
-- el sistema registra y mide sus parlays.
ALTER TABLE picks ADD COLUMN book_odds JSONB;
