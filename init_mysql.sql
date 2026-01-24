CREATE DATABASE IF NOT EXISTS mentobe;
USE mentobe;

CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(255),
    password VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    quota INT DEFAULT 3,
    vip_level INT DEFAULT 0,
    vip_expire_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36),
    stripe_session_id VARCHAR(255),
    amount_total INT,
    currency VARCHAR(10),
    status VARCHAR(50),
    price_id VARCHAR(255),
    vip_level INT,
    vip_duration VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_quotas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36),
    date DATE NOT NULL,
    count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tarot_interpretations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36),
    question TEXT,
    spread_type VARCHAR(50),
    cards JSON,
    interpretation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
