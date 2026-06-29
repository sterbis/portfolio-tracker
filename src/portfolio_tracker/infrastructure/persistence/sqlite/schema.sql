CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS  institution_account (
    id INTEGER PRIMARY KEY,
    institution_account_id TEXT NOT NULL UNIQUE,
    institution_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    encrypted_credentials TEXT,
    created_on TEXT NOT NULL,
    last_synced_at TEXT,

    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asset_account (
    id INTEGER PRIMARY KEY,
    asset_account_id TEXT NOT NULL UNIQUE,
    external_id TEXT NOT NULL,
    institution_account_id TEXT NOT NULL,
    name TEXT NOT NULL,

    FOREIGN KEY (institution_account_id) REFERENCES institution_account(institution_account_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instrument (
    id INTEGER PRIMARY KEY,
    instrument_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    currency TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bond (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    isin TEXT NOT NULL,
    face_value TEXT NOT NULL,
    coupon_rate TEXT NOT NULL,
    coupon_frequency TEXT NOT NULL,
    maturity_on TEXT
);

CREATE TABLE IF NOT EXISTS cfd (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    underlying_instrument_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    leverage TEXT NOT NULL,

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
    expiration_on TEXT NOT NULL,
    multiplier INTEGER NOT NULL,

    FOREIGN KEY (underlying_instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS option (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    underlying_instrument_id TEXT NOT NULL,
    isin TEXT,
    expiration_on TEXT NOT NULL,
    option_type TEXT NOT NULL,
    strike_price TEXT NOT NULL,
    multiplier INTEGER NOT NULL,

    FOREIGN KEY (underlying_instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS stock (
    instrument_id TEXT PRIMARY KEY REFERENCES instrument(instrument_id) ON DELETE CASCADE,
    isin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transaction (
    id INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    correlation_id TEXT,
    executed_at TEXT NOT NULL,
    asset_account_id TEXT NOT NULL,
    type TEXT NOT NULL,
    instrument_id TEXT,
    quantity TEXT NOT NULL,
    price_amount TEXT NOT NULL,
    price_currency TEXT NOT NULL,
    fee_amount TEXT NOT NULL,
    fee_currency TEXT NOT NULL,
    tax_amount TEXT NOT NULL,
    tax_currency TEXT NOT NULL,
    cash_impact_amount TEXT NOT NULL,
    cash_impact_currency TEXT NOT NULL,

    FOREIGN KEY (asset_account_id) REFERENCES asset_account(asset_account_id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS fx_rate (
    effective_on TEXT NOT NULL,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate TEXT NOT NULL,

    PRIMARY KEY (effective_on, base_currency, quote_currency)
);

CREATE TABLE IF NOT EXISTS stock_split (
    instrument_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    ratio TEXT NOT NULL,

    PRIMARY KEY (instrument_id, executed_at),
    FOREIGN KEY (instrument_id) REFERENCES instrument(instrument_id)
);
