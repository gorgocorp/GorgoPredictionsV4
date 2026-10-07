-- La API manda nombres con entidades HTML ("Sharpe Day&apos;Ron"). La ingesta ya las convierte;
-- esto corrige lo guardado antes.
UPDATE players SET name = replace(replace(name, '&apos;', ''''), '&amp;', '&')
WHERE name LIKE '%&apos;%' OR name LIKE '%&amp;%';

UPDATE picks SET description = replace(replace(description, '&apos;', ''''), '&amp;', '&')
WHERE description LIKE '%&apos;%' OR description LIKE '%&amp;%';
