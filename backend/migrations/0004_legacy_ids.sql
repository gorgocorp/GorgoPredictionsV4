-- Correspondencia entre los IDs de los proyectos anteriores (GorgoNBAParlays, GorgoPredictionsV3) y los de
-- V4 para lo que se renumera al importar: en core, las ingestas, picks, parlays y apuestas de los dos
-- proyectos chocaban entre sí. Las tablas de cada deporte conservan sus IDs.
CREATE TABLE core.legacy_ids (
    sport TEXT NOT NULL CHECK (sport IN ('nba', 'futbol')),
    entity TEXT NOT NULL CHECK (entity IN ('ingest_run', 'pick', 'parlay', 'user_bet')),
    legacy_id BIGINT NOT NULL,
    id BIGINT NOT NULL,
    PRIMARY KEY (sport, entity, legacy_id),
    CONSTRAINT legacy_ids_target_unique UNIQUE (entity, id)
);
