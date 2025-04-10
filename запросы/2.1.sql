SELECT 
    d.name AS "Отдел",
    CASE 
        WHEN p.name LIKE '%а' OR p.name LIKE '%я' THEN 'г-жа ' || p.name
        ELSE 'г-н ' || p.name
    END AS "Сотрудник"
FROM 
    Personal p
JOIN 
    Department d ON p.id_dep = d.id
ORDER BY 
    d.name, p.name;