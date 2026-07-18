CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS  institution_account (
    id INTEGER PRIMARY KEY,
    institution_account_id TEXT NOT NULL UNIQUE,
    institution_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_on DATE NOT NULL,
    last_synced_at DATETIME NOT NULL,

    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY,
    institution_account_id TEXT NOT NULL UNIQUE,
    encrypted_value TEXT NOT NULL,
    key_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_on DATE NOT NULL,
    rotated_on DATE,

    FOREIGN KEY (institution_account_id) REFERENCES institution_account(institution_account_id)
);

CREATE TABLE IF NOT EXISTS asset_account (
    id INTEGER PRIMARY KEY,
    asset_account_id TEXT NOT NULL UNIQUE,
    external_id TEXT NOT NULL,
    institution_account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

    FOREIGN KEY (institution_account_id) REFERENCES institution_account(institution_account_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instrument (
    id INTEGER PRIMARY KEY,
    instrument_id TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    currency TEXT NOT NULL,
    last_synced_at DATETIME,
);

CREATE TABLE IF NOT EXISTS bond (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    isin TEXT NOT NULL,
    face_value DECIMAL_AS_TEXT NOT NULL,
    coupon_rate DECIMAL_AS_TEXT NOT NULL,
    coupon_frequency TEXT NOT NULL,
    maturity_on DATE
);

CREATE TABLE IF NOT EXISTS cfd (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    underlying_instrument_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    leverage DECIMAL_AS_TEXT NOT NULL,

    FOREIGN KEY (underlying_instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS commodity (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    unit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crypto (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS etf (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    isin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS future (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    underlying_instrument_id TEXT NOT NULL,
    isin TEXT,
    expiration_on DATE NOT NULL,
    multiplier INTEGER NOT NULL,

    FOREIGN KEY (underlying_instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS option (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    underlying_instrument_id TEXT NOT NULL,
    isin TEXT,
    expiration_on DATE NOT NULL,
    option_type TEXT NOT NULL,
    strike_price DECIMAL_AS_TEXT NOT NULL,
    multiplier INTEGER NOT NULL,

    FOREIGN KEY (underlying_instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS stock (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    isin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_entry (
    id INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    correlation_id TEXT,
    checksum TEXT NOT NULL UNIQUE,
    executed_at DATETIME NOT NULL,
    asset_account_id TEXT NOT NULL,
    type TEXT NOT NULL,
    instrument_id TEXT,
    quantity DECIMAL_AS_TEXT NOT NULL,
    price MONEY NOT NULL,
    fee MONEY NOT NULL,
    tax MONEY NOT NULL,
    cash_impact MONEY NOT NULL,

    FOREIGN KEY (asset_account_id) REFERENCES asset_account(asset_account_id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS fx_rate (
    effective_on DATE NOT NULL,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate DECIMAL_AS_TEXT NOT NULL,

    PRIMARY KEY (effective_on, base_currency, quote_currency)
);

CREATE TABLE IF NOT EXISTS stock_split (
    instrument_id TEXT NOT NULL,
    executed_at DATETIME NOT NULL,
    ratio DECIMAL_AS_TEXT NOT NULL,

    PRIMARY KEY (instrument_id, executed_at),
    FOREIGN KEY (instrument_id) REFERENCES instrument(instrument_id)
);
