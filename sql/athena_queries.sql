-- ============================================================
-- QUERIES ANALÍTICAS — CAFETERÍA JAPONESA 2024
-- Base de datos: gastronomic_db (AWS Athena)
-- Autor: Rodolfo Moreno | github.com/rmoreno-dev
-- ============================================================

-- Q1: Ingresos por mes
-- Objetivo: identificar tendencia mensual y estacionalidad
SELECT month_name, month,
       SUM(total)   AS ingresos_totales,
       COUNT(*)     AS transacciones,
       AVG(total)   AS ticket_promedio
FROM gastronomic_db.transactions
GROUP BY month_name, month
ORDER BY month;

-- Q2: Ingresos por método de pago
-- Objetivo: entender canales de cobro y preferencias del cliente
SELECT metodo_pago_clean,
       SUM(total)  AS ingresos,
       COUNT(*)    AS transacciones,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct_transacciones
FROM gastronomic_db.transactions
GROUP BY metodo_pago_clean
ORDER BY ingresos DESC;

-- Q3: Top 10 productos por ingresos
-- Objetivo: identificar productos estrella del menú
SELECT producto, seccion,
       SUM(revenue)  AS ingresos_totales,
       COUNT(*)      AS unidades_vendidas,
       AVG(precio)   AS precio_promedio
FROM gastronomic_db.items
GROUP BY producto, seccion
ORDER BY ingresos_totales DESC
LIMIT 10;

-- Q4: Clasificación de menú (Kasavana & Smith, 1982)
-- Objetivo: distribución de rentabilidad por categoría
SELECT clasificacion_menu,
       COUNT(*)            AS productos,
       SUM(ingresos_totales) AS ingresos,
       ROUND(SUM(ingresos_totales) * 100.0 /
             SUM(SUM(ingresos_totales)) OVER(), 2) AS pct_ingresos
FROM gastronomic_db.products
GROUP BY clasificacion_menu
ORDER BY ingresos DESC;

-- Q5: Ingresos por franja horaria
-- Objetivo: optimizar staffing y producción por turno
SELECT franja_horaria,
       SUM(total)   AS ingresos,
       COUNT(*)     AS transacciones,
       AVG(total)   AS ticket_promedio
FROM gastronomic_db.transactions
GROUP BY franja_horaria
ORDER BY ingresos DESC;

-- Q6: Ingresos por día de semana
-- Objetivo: planificación operacional semanal
SELECT day_of_week,
       SUM(total)   AS ingresos,
       COUNT(*)     AS transacciones,
       AVG(total)   AS ticket_promedio
FROM gastronomic_db.transactions
GROUP BY day_of_week
ORDER BY ingresos DESC;

-- Q7: Comparativo fin de semana vs semana
-- Objetivo: validar H2 (fin de semana genera más ingresos)
SELECT CASE WHEN is_weekend THEN 'Fin de semana' ELSE 'Semana' END AS periodo,
       SUM(total)   AS ingresos_totales,
       COUNT(*)     AS transacciones,
       AVG(total)   AS ticket_promedio
FROM gastronomic_db.transactions
GROUP BY is_weekend;

-- Q8: Top 5 secciones por ingresos
-- Objetivo: identificar categorías líderes del negocio
SELECT seccion,
       SUM(revenue)  AS ingresos_totales,
       COUNT(*)      AS unidades_vendidas,
       COUNT(DISTINCT producto) AS productos_unicos
FROM gastronomic_db.items
GROUP BY seccion
ORDER BY ingresos_totales DESC
LIMIT 5;