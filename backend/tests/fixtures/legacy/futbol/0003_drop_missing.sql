-- El ajuste de goles por bajas se quitó: en el backtest empeoraba el pronóstico (ver team_model.py).
ALTER TABLE fixture_projections
    DROP COLUMN home_missing,
    DROP COLUMN away_missing;
