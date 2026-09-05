BEGIN;

-- Preserve values that were previously withheld only because the source scale
-- was unknown. The arithmetic uses the raw magnitudes reported by SMV and NULL
-- deliberately means "scale not verified"; it must not be inferred downstream.
UPDATE metric_values
SET
    status = 'computed',
    value = CASE metric_code
        WHEN 'working_capital' THEN
            (inputs->'current_assets'->>'current')::numeric
            - (inputs->'current_liabilities'->>'current')::numeric
        WHEN 'total_debt' THEN
            (inputs->'current_borrowings'->>'current')::numeric
            + (inputs->'non_current_borrowings'->>'current')::numeric
        WHEN 'net_debt' THEN
            (inputs->'current_borrowings'->>'current')::numeric
            + (inputs->'non_current_borrowings'->>'current')::numeric
            - (inputs->'cash_and_cash_equivalents'->>'current')::numeric
        WHEN 'free_cash_flow' THEN
            (inputs->'operating_cash_flow'->>'current')::numeric
            + (inputs->'purchases_property_plant_equipment'->>'current')::numeric
    END,
    currency_code = CASE metric_code
        WHEN 'working_capital' THEN inputs->'current_assets'->>'currency_code'
        WHEN 'total_debt' THEN inputs->'current_borrowings'->>'currency_code'
        WHEN 'net_debt' THEN inputs->'current_borrowings'->>'currency_code'
        WHEN 'free_cash_flow' THEN inputs->'operating_cash_flow'->>'currency_code'
    END,
    value_scale = NULL,
    reason = NULL,
    calculated_at = NOW()
WHERE status = 'not_available'
  AND reason = 'La escala monetaria todavía no fue verificada'
  AND metric_code IN ('working_capital', 'total_debt', 'net_debt', 'free_cash_flow');

COMMIT;
