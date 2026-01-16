SELECT
      category,
      COUNT(*) as rows,
      SUM(units_sold) as units,
      SUM(revenue) as revenue
  FROM sales_facts_mv
  GROUP BY category
  ORDER BY revenue DESC;