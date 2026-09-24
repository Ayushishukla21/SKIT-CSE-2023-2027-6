-- SmartCart AI - MySQL schema
-- Matches docs/API_CONTRACT.md v1.0 and docs/DATA_SCHEMA.md v1.0
--
-- Usage (after creating an empty `smartcart` database):
--   mysql -u root -p smartcart < schema.sql

CREATE TABLE IF NOT EXISTS platforms (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Fixed platform IDs - never change these (see API_CONTRACT.md section 1)
INSERT INTO platforms (id, name) VALUES
    (1, 'Blinkit'),
    (2, 'Zepto'),
    (3, 'Instamart'),
    (4, 'Flipkart Minutes')
ON DUPLICATE KEY UPDATE name = VALUES(name);

CREATE TABLE IF NOT EXISTS products (
    id         INT PRIMARY KEY,
    name       VARCHAR(150) NOT NULL,
    brand      VARCHAR(80)  NOT NULL,
    category   VARCHAR(50)  NOT NULL,
    quantity   DECIMAL(10,2) NOT NULL,
    unit       VARCHAR(10)  NOT NULL,
    image_url  VARCHAR(255) NULL
);

CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_products_name ON products (name);
CREATE INDEX idx_products_brand ON products (brand);

-- One CURRENT price per product per platform (this milestone has no history table)
CREATE TABLE IF NOT EXISTS prices (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    product_id  INT NOT NULL,
    platform_id INT NOT NULL,
    price       DECIMAL(10,2) NULL,     -- NULL only when available = FALSE
    currency    VARCHAR(10) NOT NULL DEFAULT 'INR',
    available   BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at  DATETIME NOT NULL,
    CONSTRAINT fk_prices_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_prices_platform
        FOREIGN KEY (platform_id) REFERENCES platforms (id) ON DELETE CASCADE,
    CONSTRAINT uq_prices_product_platform UNIQUE (product_id, platform_id)
);

CREATE TABLE IF NOT EXISTS offers (
    id               INT PRIMARY KEY,
    product_id       INT NOT NULL,
    platform_id      INT NOT NULL,
    title            VARCHAR(100) NOT NULL,
    description      TEXT NULL,
    discount_amount  DECIMAL(10,2) NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_offers_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_offers_platform
        FOREIGN KEY (platform_id) REFERENCES platforms (id) ON DELETE CASCADE
);

CREATE INDEX idx_offers_product_platform ON offers (product_id, platform_id);

-- Reserved for a later milestone (see DATA_SCHEMA.md section 8) - not used yet:
-- price_history, users, recommendations, alerts, budgets, product_aliases
