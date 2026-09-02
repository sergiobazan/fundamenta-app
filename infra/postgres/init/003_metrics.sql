BEGIN;

CREATE TABLE IF NOT EXISTS metric_definitions (
    code TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('monetary', 'ratio', 'percentage')),
    formula_version INTEGER NOT NULL CHECK (formula_version > 0),
    formula_expression TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metric_values (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    period_code TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    metric_code TEXT NOT NULL REFERENCES metric_definitions(code),
    formula_version INTEGER NOT NULL CHECK (formula_version > 0),
    status TEXT NOT NULL CHECK (status IN ('computed', 'not_available')),
    value NUMERIC(38, 12),
    currency_code TEXT,
    value_scale TEXT CHECK (value_scale IN ('units', 'thousands', 'millions')),
    reason TEXT,
    inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (
        company_id, fiscal_year, period_code, scope, metric_code, formula_version
    ),
    CHECK (
        (status = 'computed' AND value IS NOT NULL AND reason IS NULL)
        OR (status = 'not_available' AND value IS NULL AND reason IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS metric_values_company_period_idx
    ON metric_values (company_id, fiscal_year DESC, period_code, scope);

INSERT INTO metric_definitions (
    code, display_name, description, value_kind, formula_version, formula_expression
) VALUES
    ('revenue_growth', 'Crecimiento de ingresos',
     'Variación de ingresos frente al importe comparativo.', 'percentage', 1,
     '(revenue_current / revenue_comparative) - 1'),
    ('gross_margin', 'Margen bruto',
     'Utilidad bruta como proporción de los ingresos.', 'percentage', 1,
     'gross_profit / revenue'),
    ('operating_margin', 'Margen operativo',
     'Utilidad operativa como proporción de los ingresos.', 'percentage', 1,
     'operating_profit / revenue'),
    ('net_margin', 'Margen neto',
     'Utilidad neta como proporción de los ingresos.', 'percentage', 1,
     'net_profit / revenue'),
    ('current_ratio', 'Razón corriente',
     'Activos corrientes divididos entre pasivos corrientes.', 'ratio', 1,
     'current_assets / current_liabilities'),
    ('working_capital', 'Capital de trabajo',
     'Activos corrientes menos pasivos corrientes.', 'monetary', 1,
     'current_assets - current_liabilities'),
    ('total_debt', 'Deuda financiera total',
     'Pasivos financieros corrientes y no corrientes.', 'monetary', 1,
     'current_borrowings + non_current_borrowings'),
    ('net_debt', 'Deuda financiera neta',
     'Deuda financiera total menos efectivo y equivalentes.', 'monetary', 1,
     'current_borrowings + non_current_borrowings - cash_and_cash_equivalents'),
    ('debt_to_equity', 'Deuda financiera sobre patrimonio',
     'Deuda financiera total dividida entre patrimonio.', 'ratio', 1,
     '(current_borrowings + non_current_borrowings) / total_equity'),
    ('liabilities_to_equity', 'Pasivos sobre patrimonio',
     'Pasivos totales divididos entre patrimonio.', 'ratio', 1,
     'total_liabilities / total_equity'),
    ('return_on_assets', 'ROA',
     'Utilidad neta sobre activos promedio.', 'percentage', 1,
     'net_profit / average(total_assets_current, total_assets_comparative)'),
    ('return_on_equity', 'ROE',
     'Utilidad neta sobre patrimonio promedio.', 'percentage', 1,
     'net_profit / average(total_equity_current, total_equity_comparative)'),
    ('operating_cash_flow_margin', 'Margen de flujo operativo',
     'Flujo operativo como proporción de ingresos.', 'percentage', 1,
     'operating_cash_flow / revenue'),
    ('free_cash_flow', 'Flujo de caja libre',
     'Flujo operativo más compras de propiedades, planta y equipo reportadas con signo.',
     'monetary', 1,
     'operating_cash_flow + purchases_property_plant_equipment'),
    ('free_cash_flow_margin', 'Margen de flujo de caja libre',
     'Flujo de caja libre como proporción de ingresos.', 'percentage', 1,
     '(operating_cash_flow + purchases_property_plant_equipment) / revenue')
ON CONFLICT (code) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    value_kind = EXCLUDED.value_kind,
    formula_version = EXCLUDED.formula_version,
    formula_expression = EXCLUDED.formula_expression,
    updated_at = NOW();

COMMIT;

