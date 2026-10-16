-- Illustrative assumptions; costs are scenario estimates, not actual spending.
WITH workload AS (
  SELECT m.city, m.country, m.stage, m.matches,
         a.staff_per_match, a.hours_per_shift, a.hourly_rate_cad
  FROM match_inventory m JOIN stage_assumptions a ON m.stage=a.stage
), scenario_costs AS (
  SELECT w.*, s.scenario, s.staff_multiplier,
    CAST(w.staff_per_match*s.staff_multiplier AS INTEGER)
      + CASE WHEN w.staff_per_match*s.staff_multiplier > CAST(w.staff_per_match*s.staff_multiplier AS INTEGER)
             THEN 1 ELSE 0 END AS adjusted_staff
  FROM workload w CROSS JOIN scenarios s
), totals AS (
  SELECT scenario, city, country, SUM(matches) AS matches,
    SUM(matches*adjusted_staff) AS staff_shifts,
    SUM(matches*adjusted_staff*hours_per_shift) AS staff_hours,
    SUM(matches*adjusted_staff*hours_per_shift*hourly_rate_cad) AS labor_cost_cad
  FROM scenario_costs GROUP BY scenario, city, country
)
SELECT *, RANK() OVER(PARTITION BY scenario ORDER BY labor_cost_cad DESC) AS cost_rank,
  100.0*labor_cost_cad/SUM(labor_cost_cad) OVER(PARTITION BY scenario) AS cost_share_pct
FROM totals ORDER BY scenario, cost_rank, city;
