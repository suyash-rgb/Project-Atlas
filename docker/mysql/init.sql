-- MySQL Initialization Script for Project Atlas
-- Sets up project_atlas database, read-write user, read-only user, and seed data

CREATE DATABASE IF NOT EXISTS project_atlas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE project_atlas;

-- 1. Create Tables
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    published DATE NOT NULL,
    sector VARCHAR(128) NOT NULL,
    access VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS market_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report VARCHAR(32) NOT NULL,
    metric VARCHAR(128) NOT NULL,
    region VARCHAR(64) NOT NULL,
    year_period VARCHAR(64) NOT NULL,
    value VARCHAR(64) NOT NULL,
    scope_note TEXT,
    FOREIGN KEY (report) REFERENCES reports(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR(32) PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    purchased_reports TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS escalations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id VARCHAR(32) NOT NULL,
    question TEXT NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id VARCHAR(32) NOT NULL,
    message_id VARCHAR(128) NOT NULL,
    rating VARCHAR(16) NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Seed Reports
INSERT IGNORE INTO reports (id, title, publisher, published, sector, access) VALUES
('R-101', 'Global Smart Water Meter Market 2025', 'CMR', '2025-03-10', 'Utilities', 'paid'),
('R-102', 'Smart Water Metering: Industry Outlook 2024', 'Aquila Insights (third party)', '2024-06-18', 'Utilities', 'public excerpt'),
('R-103', 'Residential Water Purifier Market 2025', 'CMR', '2025-01-22', 'Consumer Durables', 'paid'),
('R-104', 'Commercial & Industrial RO Membrane Systems 2025', 'CMR', '2025-02-14', 'Industrial Equipment', 'paid'),
('R-105', 'Smart Multi-Utility Metering Infrastructure 2024', 'Apex Grid Insights (third party)', '2024-08-05', 'Utilities', 'public excerpt'),
('R-106', 'Decentralized Wastewater Recycling Systems 2025', 'CMR', '2025-02-28', 'Cleantech', 'paid');

-- 3. Seed Market Metrics
INSERT IGNORE INTO market_metrics (id, report, metric, region, year_period, value, scope_note) VALUES
(1, 'R-101', 'Market size', 'Global', '2024', 'USD 4.21 B', 'Includes hardware, software and services'),
(2, 'R-101', 'CAGR', 'Global', '2025-2030', '11.2 %', 'Forecast period stated as 2025-2030'),
(3, 'R-101', 'Regional share', 'APAC', '2024', '38 %', 'Share of global market size'),
(4, 'R-102', 'Market size', 'Global', '2024', 'USD 3.87 B', 'AMR / AMI hardware only'),
(5, 'R-102', 'CAGR', 'Global', '2024-2029', '9.8 %', 'Different forecast window from R-101'),
(6, 'R-102', 'Regional share', 'APAC', '2024', '41 %', 'Share of hardware market'),
(7, 'R-103', 'Market size', 'Global', '2024', 'USD 9.85 B', 'Point-of-use residential filtration systems'),
(8, 'R-103', 'CAGR', 'Global', '2025-2030', '8.9 %', 'Forecast period 2025-2030'),
(9, 'R-103', 'Regional share', 'APAC', '2024', '48 %', 'Largest regional consumer market'),
(10, 'R-104', 'Market size', 'Global', '2024', 'USD 14.20 B', 'High-capacity industrial RO and membrane separation'),
(11, 'R-104', 'CAGR', 'Global', '2024-2030', '7.4 %', 'Forecast period 2024-2030'),
(12, 'R-104', 'Regional share', 'North America', '2024', '36 %', 'Pharma and energy sector capex dominance'),
(13, 'R-105', 'Market size', 'Global', '2024', 'USD 11.50 B', 'Combined electric, water, and gas AMI systems'),
(14, 'R-105', 'CAGR', 'Global', '2024-2029', '10.1 %', '5-year multi-utility outlook'),
(15, 'R-105', 'Regional share', 'Europe', '2024', '35 %', 'Mandated multi-commodity smart grid rollouts'),
(16, 'R-106', 'Market size', 'Global', '2024', 'USD 7.60 B', 'Modular MBR/MBBR packaged wastewater plants'),
(17, 'R-106', 'CAGR', 'Global', '2025-2030', '12.5 %', 'Highest growth segment in water cleantech'),
(18, 'R-106', 'Regional share', 'APAC', '2024', '44 %', 'Municipal effluent reuse mandates');

-- 4. Seed Clients
INSERT IGNORE INTO clients (id, company, contact_email, purchased_reports) VALUES
('C-01', 'Northwind Utilities', 'ops@northwind.example.com', 'R-101, R-103'),
('C-02', 'Blue Delta Infra', 'procurement@bluedelta.example.com', 'R-103'),
('C-03', 'AquaTech Industrial Corp', 'research@aquatech.example.com', 'R-104, R-106'),
('C-04', 'City of Austin Water Utility', 'ami-lead@austin.gov.example.com', 'R-101'),
('C-05', 'Global Grid Analytics', 'subs@globalgrid.example.com', 'R-105'),
('C-06', 'Public Tier Evaluation', 'visitor@cmr-trial.example.com', '');

-- 5. Create Read-Only User for Agent SQL Tool
CREATE USER IF NOT EXISTS 'atlas_readonly'@'%' IDENTIFIED BY 'atlas_readonly_password';
GRANT SELECT ON project_atlas.* TO 'atlas_readonly'@'%';

-- 6. Create Read-Write User for Backend/Portal
CREATE USER IF NOT EXISTS 'atlas_user'@'%' IDENTIFIED BY 'atlas_password';
GRANT ALL PRIVILEGES ON project_atlas.* TO 'atlas_user'@'%';

FLUSH PRIVILEGES;
