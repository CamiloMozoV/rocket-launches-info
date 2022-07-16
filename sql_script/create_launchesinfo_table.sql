CREATE TABLE IF NOT EXISTS launches_info (
    service_provider_name VARCHAR(100),
    service_provider_type VARCHAR(50),
    slug VARCHAR(50),
    rocket_full_name VARCHAR(50),
    window_start TIMESTAMP,
    window_end TIMESTAMP
);