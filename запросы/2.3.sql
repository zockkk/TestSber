WITH MinSalaries AS (
    SELECT 
        p.id_dep,
        p.name,
        p.sal,
        d.name AS dep_name,
        RANK() OVER (PARTITION BY p.id_dep ORDER BY p.sal ASC) AS rank_min
    FROM 
        Personal p
    JOIN 
        Department d ON p.id_dep = d.id
),
MaxSalaries AS (
    SELECT 
        p.id_dep,
        p.name,
        p.sal,
        d.name AS dep_name,
        RANK() OVER (PARTITION BY p.id_dep ORDER BY p.sal DESC) AS rank_max
    FROM 
        Personal p
    JOIN 
        Department d ON p.id_dep = d.id
)

SELECT 
    m.dep_name AS "Отдел",
    STRING_AGG(DISTINCT 
        CASE WHEN m.rank_min = 1 THEN m.name || ' (' || m.sal || ')' END, 
        ', ' ORDER BY m.name) AS "Сотрудники с мин. зарплатой",
    STRING_AGG(DISTINCT 
        CASE WHEN x.rank_max = 1 THEN x.name || ' (' || x.sal || ')' END, 
        ', ' ORDER BY x.name) AS "Сотрудники с макс. зарплатой"
FROM 
    MinSalaries m
JOIN 
    MaxSalaries x ON m.id_dep = x.id_dep
WHERE 
    m.rank_min = 1 OR x.rank_max = 1
GROUP BY 
    m.dep_name
ORDER BY 
    m.dep_name;