-- Seed Initial Solar Plants
INSERT INTO plants (plant_id, plant_name, capacity_mw, location, default_tariff_inr, inverter_count)
VALUES 
    ('SP-01', 'Pavagada Solar Park', 50.0, 'Tumakuru, Karnataka', 3.25, 4),
    ('SP-02', 'Bhadla Solar Park', 75.0, 'Phalodi, Rajasthan', 2.95, 6),
    ('SP-03', 'Rewa Ultra Mega Solar', 40.0, 'Rewa, Madhya Pradesh', 3.40, 4),
    ('SP-04', 'Charanka Solar Park', 30.0, 'Patan, Gujarat', 3.15, 3)
ON CONFLICT (plant_id) DO UPDATE SET
    plant_name = EXCLUDED.plant_name,
    capacity_mw = EXCLUDED.capacity_mw,
    default_tariff_inr = EXCLUDED.default_tariff_inr;

-- Seed Default Tariff Configs
INSERT INTO tariff_configs (plant_id, category, tariff_inr, effective_from)
VALUES
    ('SP-01', 'Grid Export', 3.25, '2025-01-01 00:00:00'),
    ('SP-01', 'Self Consumption', 4.39, '2025-01-01 00:00:00'),
    ('SP-02', 'Grid Export', 2.95, '2025-01-01 00:00:00'),
    ('SP-02', 'Self Consumption', 3.98, '2025-01-01 00:00:00'),
    ('SP-03', 'Grid Export', 3.40, '2025-01-01 00:00:00'),
    ('SP-03', 'Self Consumption', 4.59, '2025-01-01 00:00:00'),
    ('SP-04', 'Grid Export', 3.15, '2025-01-01 00:00:00'),
    ('SP-04', 'Self Consumption', 4.25, '2025-01-01 00:00:00');

-- Seed Inverter Gateways
INSERT INTO inverter_gateways (manufacturer, plant_id, site_id, status)
VALUES
    ('SolarEdge', 'SP-01', 'SE-SITE-PVG', 'NOT_CONFIGURED'),
    ('SMA', 'SP-02', 'SMA-BHD-CLUSTER', 'NOT_CONFIGURED'),
    ('Fronius', 'SP-03', 'FRO-RWA-01', 'NOT_CONFIGURED'),
    ('Sungrow', 'SP-04', 'SG-CRK-PARK', 'NOT_CONFIGURED'),
    ('Huawei', 'SP-01', 'HW-FUSION-PVG', 'NOT_CONFIGURED')
ON CONFLICT (manufacturer, plant_id, site_id) DO NOTHING;
