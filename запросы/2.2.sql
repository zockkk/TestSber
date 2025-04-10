SELECT 
    name AS "Сотрудник",
    LENGTH(REGEXP_REPLACE(LOWER(name), '[^аеёиоуыэюя]', '', 'g')) AS "Кол-во гласных"
FROM 
    Personal
ORDER BY 
    "Кол-во гласных" DESC, name;