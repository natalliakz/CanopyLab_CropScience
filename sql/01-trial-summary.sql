-- Plain SQL. This project contains synthetic data and analysis created for
-- demonstration purposes only.
--
-- Open this file in Positron with the DuckDB connection selected in the
-- Connections pane, then run it (Cmd/Ctrl+Enter). The result lands in the Data
-- Explorer, where you can sort and filter it without writing another query.
--
-- Connection: data/synthetic-agronomy.duckdb

SELECT
    season,
    treatment,
    count(*)                              AS plots,
    round(avg(yield_t_ha), 2)             AS mean_yield_t_ha,
    round(stddev(yield_t_ha), 2)          AS sd_yield_t_ha,
    round(avg(disease_pressure_index), 1) AS mean_disease_index,
    round(avg(rainfall_mm), 0)            AS mean_rainfall_mm
FROM field_trials
GROUP BY season, treatment
ORDER BY season, treatment;
