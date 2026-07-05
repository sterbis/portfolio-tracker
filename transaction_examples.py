from dataclasses import dataclass
from datetime import datetime, date
from enum import StrEnum
from decimal import Decimal


# --- Enums ---
class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    CASH = "CASH"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    BOND = "BOND"
    REAL_ESTATE = "REAL_ESTATE"


class InstrumentType(StrEnum):
    STOCK = "STOCK"
    ETF = "ETF"
    CURRENCY = "CURRENCY"
    CRYPTO = "CRYPTO"
    BOND = "BOND"
    MUTUAL_FUND = "MUTUAL_FUND"
    CFD = "CFD"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    INDEX = "INDEX"
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    PROPERTY = "PROPERTY"
    PHYSICAL_COMMODITY = "PHYSICAL_COMMODITY"


class TransactionType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
    CURRENCY_EXCHANGE = "CURRENCY_EXCHANGE"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    TAX = "TAX"
    INTEREST = "INTEREST"
    STAKING_REWARD = "STAKING_REWARD"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class CouponFrequency(StrEnum):
    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"


# --- Infrastructure / Account Layout ---
@dataclass
class Institution:
    id: str
    name: str


@dataclass
class InstitutionAccount:
    id: str
    institution_id: str
    name: str
    credentials: dict[str, str] | None = None


@dataclass
class AssetAccount:
    id: str
    institution_account_id: str
    name: str
    account_type: str  # cash, margin, physical_vault


# --- Pure, Stateless Instruments ---
@dataclass(frozen=True)
class Instrument:
    id: str
    type: InstrumentType
    symbol: str
    name: str
    currency: str  # Base asset currency
    asset_class: AssetClass
    exchange: str | None


@dataclass(frozen=True)
class Currency(Instrument): ...


@dataclass(frozen=True)
class CryptoCurrency(Instrument): ...


@dataclass(frozen=True)
class Stock(Instrument):
    isin: str


@dataclass(frozen=True)
class Etf(Instrument):
    isin: str


@dataclass(frozen=True)
class Bond(Instrument):
    isin: str
    face_value: Decimal
    coupon_rate: Decimal
    coupon_frequency: CouponFrequency
    maturity_date: date


@dataclass(frozen=True)
class Commodity(Instrument):
    unit: str


@dataclass(frozen=True)
class DerivativeInstrument(Instrument):
    underlying_instrument_id: str


@dataclass(frozen=True)
class Cfd(DerivativeInstrument):
    leverage: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class Future(DerivativeInstrument):
    settlement_date: date
    multiplier: int


@dataclass(frozen=True)
class Option(DerivativeInstrument):
    option_type: str  # CALL, PUT
    strike_price: Decimal
    expiration_date: date
    multiplier: int


# --- The Transaction Ledger ---
@dataclass
class Transaction:
    id: str  # Idempotency Hash
    correlation_id: str | None
    asset_account_id: str
    timestamp: datetime
    type: TransactionType
    instrument_id: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    tax: Decimal
    currency: str  # Execution Currency
    cash_impact: Decimal


institution_t212 = Institution(
    id="institut_001",
    name="Trading 212",
)

institution_account_t212 = InstitutionAccount(
    id="i_acc_001",
    institution_id="institut_001",
    name="My first Trading 212 account",
    credentials=None,
)

asset_account_t212 = AssetAccount(
    id="a_acc_001",
    institution_account_id="i_acc_001",
    name="testing portfolio",
    account_type="margin",
)

instrument_czk = Currency(
    id="inst_001",
    type=InstrumentType.CURRENCY,
    symbol="CZK",
    name="Ceska Koruna",
    currency="CZK",
    asset_class=AssetClass.CASH,
    exchange=None,
)

transaction_deposit = Transaction(
    id="tr_001",
    correlation_id=None,
    asset_account_id="a_acc_001",
    timestamp=datetime.now(),
    type=TransactionType.DEPOSIT,
    instrument_id="inst_001",
    quantity=Decimal(100000),
    price=Decimal(1),
    fee=Decimal(0),
    tax=Decimal(0),
    currency="CZK",
    cash_impact=Decimal(100000),
)

instrument_usd = Currency(
    id="inst_002",
    type=InstrumentType.CURRENCY,
    symbol="USD",
    name="United States Dollar",
    currency="USD",
    asset_class=AssetClass.CASH,
    exchange=None,
)

# Leg 1: The CZK perspective
transaction_currency_exchange_leg_1 = Transaction(
    id="tr_002_czk",
    correlation_id="abcde",
    asset_account_id="a_acc_001",
    timestamp=datetime.now(),
    type=TransactionType.CURRENCY_EXCHANGE,
    instrument_id="inst_001",  # CZK Instrument
    quantity=Decimal("100000.00"),
    price=Decimal("20.00"),  # FX Rate (20 CZK = 1 USD)
    fee=Decimal("150.00"),  # 150 CZK fee
    tax=Decimal("0.00"),
    currency="CZK",  # Everything in this row is CZK
    cash_impact=Decimal("-100000.00"),  # Exactly 100k CZK left the account
)

# Leg 2: The USD perspective
transaction_currency_exchange_leg_2 = Transaction(
    id="tr_002_usd",
    correlation_id="abcde",
    asset_account_id="a_acc_001",
    timestamp=datetime.now(),
    type=TransactionType.CURRENCY_EXCHANGE,
    instrument_id="inst_002",  # USD Instrument
    quantity=Decimal("4992.50"),
    price=Decimal("20.00"),  # Same FX Rate for clarity
    fee=Decimal("0.00"),
    tax=Decimal("0.00"),
    currency="USD",  # Everything in this row is USD
    cash_impact=Decimal("4992.50"),  # Exactly 4992.50 USD entered the account
)

instrument_aapl = Stock(
    id="inst_aapl_001",
    type=InstrumentType.STOCK,
    symbol="AAPL",
    name="Apple Inc.",
    currency="USD",  # Base currency it trades in
    asset_class=AssetClass.EQUITY,
    exchange="NASDAQ",
    isin="US0378331005",  # Real Apple ISIN
)

transaction_buy_aapl = Transaction(
    id="tr_003_buy_aapl",
    correlation_id=None,  # Simple trade, no autoconversion needed
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 11, 10, 0, 0),
    type=TransactionType.BUY,
    instrument_id="inst_aapl_001",  # Points to Apple
    quantity=Decimal("10.00"),  # We bought 10 shares
    price=Decimal("180.00"),  # Price per share
    fee=Decimal("0.05"),  # Transaction fee in USD
    tax=Decimal("0.00"),
    currency="USD",  # This row is calculated in USD
    cash_impact=Decimal("-1800.05"),  # (10 * 180) + 0.05 = 1800.05 leaving the account
)

transaction_aapl_dividend = Transaction(
    id="tr_004_aapl_dividend",
    correlation_id=None,  # Standalone event
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 7, 15, 12, 0, 0),
    type=TransactionType.DIVIDEND,
    instrument_id="inst_aapl_001",  # Points to Apple
    quantity=Decimal("10.00"),  # The number of shares held at ex-dividend date
    price=Decimal("0.25"),  # Gross dividend per share
    fee=Decimal("0.00"),
    tax=Decimal("0.38"),  # Withholding tax deducted
    currency="USD",
    cash_impact=Decimal(
        "2.12"
    ),  # Gross ($2.50) - Tax ($0.38) = +$2.12 entering the account
)

instrument_bond_czk = Bond(
    id="inst_bond_001",
    type=InstrumentType.BOND,
    symbol="CZ2030_GOV",
    name="Czech Republic Gov 5% 2030",
    currency="CZK",
    asset_class=AssetClass.BOND,
    exchange="PSE",  # Prague Stock Exchange
    isin="abcd1234",
    face_value=Decimal("10000.00"),
    coupon_rate=Decimal("0.05"),  # 5%
    coupon_frequency=CouponFrequency.SEMI_ANNUAL,
    maturity_date=date(2030, 5, 15),
)

shared_bond_buy_id = "bond_purchase_20260611"

# --- Leg 1: The Core Bond Asset Purchase ---
transaction_bond_buy = Transaction(
    id="tr_bond_buy_01",
    correlation_id=shared_bond_buy_id,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 11, 11, 0, 0),
    type=TransactionType.BUY,
    instrument_id="inst_bond_001",
    quantity=Decimal("2.00"),  # 2 bonds
    price=Decimal("10150.00"),  # 101.5% of Face Value in CZK
    fee=Decimal("50.00"),  # Broker transaction fee
    tax=Decimal("0.00"),
    currency="CZK",
    # (2 * 10150) + 50 = -20350 CZK
    cash_impact=Decimal("-20350.00"),
)

# --- Leg 2: The Accrued Interest Outflow ---
transaction_bond_interest = Transaction(
    id="tr_bond_accrued_int_01",
    correlation_id=shared_bond_buy_id,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 11, 11, 0, 0),
    # We reuse INTEREST but with a negative impact to show we paid it out
    type=TransactionType.INTEREST,
    instrument_id="inst_bond_001",
    quantity=Decimal("2.00"),
    price=Decimal("125.00"),  # Accrued interest per bond paid to seller
    fee=Decimal("0.00"),
    tax=Decimal("0.00"),
    currency="CZK",
    cash_impact=Decimal("-250.00"),  # Outflow of cash for accrued interest
)

transaction_bond_coupon_1 = Transaction(
    id="tr_bond_coupon_20261115",
    correlation_id=None,  # Standalone event
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 11, 15, 9, 0, 0),
    type=TransactionType.INTEREST,  # Coupon income
    instrument_id="inst_bond_001",  # Connects this income to the bond asset
    quantity=Decimal("2.00"),  # You held 2 bonds
    price=Decimal("250.00"),  # Received 250 CZK per bond (2.5%)
    fee=Decimal("0.00"),
    tax=Decimal("75.00"),  # 15% local withholding tax on interest if applicable
    currency="CZK",
    # Gross (500) - Tax (75) = +425 CZK net income
    cash_impact=Decimal("425.00"),
)

# 1. The "Real" Underlying Commodity
underlying_oil = Commodity(
    id="inst_cmd_oil_001",
    type=InstrumentType.PHYSICAL_COMMODITY,
    symbol="WTI_CRUDE",
    name="West Texas Intermediate Crude Oil",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange=None,
    unit="BARREL",
)

# 2. The Tradable Futures Contract Instrument
# Standard WTI Crude Oil futures (CL) have a multiplier of 1,000 barrels per contract
oil_future_contract = Future(
    id="inst_fut_oil_202609",
    type=InstrumentType.FUTURE,
    symbol="CLU2026",  # Standard exchange ticker for Sept 2026 Future
    name="Crude Oil Light Sweet Sept 2026",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange="NYMEX",
    underlying_instrument_id="inst_cmd_oil_001",  # Points back to the real oil asset
    multiplier=1000,
    settlement_date=date(2026, 8, 20),  # Trading stops just before Sept delivery
)

transaction_buy_future = Transaction(
    id="tr_fut_buy_01",
    correlation_id=None,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 11, 15, 0, 0),
    type=TransactionType.BUY,
    instrument_id="inst_fut_oil_202609",  # Points to the Sept Future
    quantity=Decimal("1.00"),  # 1 Contract
    price=Decimal("75.00"),  # Price per unit (barrel)
    fee=Decimal("2.25"),  # Exchange execution fee (paid immediately)
    tax=Decimal("0.00"),
    currency="USD",
    cash_impact=Decimal(
        "-2.25"
    ),  # Only the broker fee leaves your cash balance right now!
)

# 1. Root Commodity
underlying_physical_oil = Commodity(
    id="inst_cmd_oil_wti",
    type=InstrumentType.PHYSICAL_COMMODITY,
    symbol="WTI_CRUDE",
    name="West Texas Intermediate Crude Oil",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange=None,
    unit="BARREL",
)

# 2. Intermediate Exchange Future
underlying_future_contract = Future(
    id="inst_fut_oil_20260618",
    type=InstrumentType.FUTURE,
    symbol="CLN2026",  # Standard ticker for July 2026 Crude Future
    name="Crude Oil Future 18Jun26",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange=None,
    underlying_instrument_id="inst_cmd_oil_wti",
    multiplier=1000,
    settlement_date=date(2026, 6, 18),
)

# 3. The Tradable T212 CFD Instrument
t212_oil_cfd = Cfd(
    id="inst_cfd_t212_oil_m26",
    type=InstrumentType.CFD,
    symbol="CRUDE",  # Trading 212 internal ticker symbol
    name="Crude Oil-18Jun26",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange="OTC",  # Over-The-Counter (provided in your data)
    underlying_instrument_id="inst_fut_oil_20260618",  # Points to the Future!
    leverage=Decimal("10.0"),  # T212 standard retail oil leverage is usually 1:10
)

transaction_t212_demo_cfd = Transaction(
    id="tr_t212_50250621181",  # Using your real Order ID
    correlation_id=None,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 10, 19, 6, 17),  # From your execution time
    type=TransactionType.BUY,
    instrument_id="inst_cfd_t212_oil_m26",  # Points to our multi-layered CFD
    quantity=Decimal("100"),  # 100 Units
    price=Decimal("90.48"),  # Execution price
    fee=Decimal("0.00"),  # Commission Free
    tax=Decimal("0.00"),
    currency="USD",
    cash_impact=Decimal("0.00"),  # Pure margin trade opening
)

# 1. The Spot Commodity (Root Asset)
underlying_gold = Commodity(
    id="inst_cmd_gold_spot",
    type=InstrumentType.PHYSICAL_COMMODITY,
    symbol="XAU",  # ISO 4217 Currency Code for Gold!
    name="Gold (Spot)",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange=None,
    unit="TROY_OUNCE",
)

# 2. The Trading 212 Spot Gold CFD
t212_gold_cfd = Cfd(
    id="inst_cfd_t212_xauusd",
    type=InstrumentType.CFD,
    symbol="XAUUSD",  # Matches the T212 Symbol
    name="Gold",
    currency="USD",
    asset_class=AssetClass.COMMODITY,
    exchange="OTC",
    underlying_instrument_id="inst_cmd_gold_spot",
    leverage=Decimal("20.0"),  # Retail brokers usually give 1:20 leverage on Gold
)

transaction_t212_gold_cfd = Transaction(
    id="tr_t212_50250621357",  # Using your exact Order ID
    correlation_id=None,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 10, 19, 8, 19),
    type=TransactionType.BUY,
    instrument_id="inst_cfd_t212_xauusd",
    quantity=Decimal("5.00"),  # 5 Units
    price=Decimal("4097.39"),  # Execution price per ounce
    fee=Decimal("0.00"),  # Commission Free
    tax=Decimal("0.00"),
    currency="USD",
    cash_impact=Decimal("0.00"),  # Margin position opened, no immediate cash outflow
)

transaction_gold_cfd_interest = Transaction(
    id="tr_t212_swap_20260610_2300",
    correlation_id=None,  # Standalone daily recurring event
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 10, 23, 0, 0),  # Charged at the 23:00 cut-off time
    type=TransactionType.FEE,  # Financial financing cost
    instrument_id="inst_cfd_t212_xauusd",  # Accurately resolved to your T212 Gold CFD
    quantity=Decimal("5.00"),  # Size of the position held
    price=Decimal("1.674022"),  # Rate per unit charged by broker
    fee=Decimal("8.37"),  # The fee itself
    tax=Decimal("0.00"),
    currency="USD",
    cash_impact=Decimal("-8.37"),  # Deducted directly from your USD balance
)

# 1. The Root Index (Pure mathematical abstraction)
underlying_nasdaq_index = Instrument(
    id="inst_idx_nasdaq100",
    type=InstrumentType.INDEX,  # Corrected to Instrument Type
    symbol="NDX",
    name="Nasdaq 100 Index",
    currency="USD",
    asset_class=AssetClass.EQUITY,  # Corrected to Asset Class Equity!
    exchange="NASDAQ",
)

# 2. The Intermediate Index Future Contract
index_future_contract = Future(
    id="inst_fut_ndx_20260617",
    type=InstrumentType.FUTURE,
    symbol="NQM2026",  # CME June 2026 Nasdaq Future
    name="E-mini Nasdaq-100 Future Jun 2026",
    currency="USD",
    asset_class=AssetClass.EQUITY,  # Inherits equity asset class
    exchange="CME",
    underlying_instrument_id="inst_idx_nasdaq100",
    multiplier=20,  # E-mini contract multiplier is $20 x Index
    settlement_date=date(2026, 6, 17),  # Your app's discovered expiry date
)

# 3. The Tradable T212 Index Future CFD
t212_tech100_cfd = Cfd(
    id="inst_cfd_t212_tech100_m26",
    type=InstrumentType.CFD,
    symbol="TECH100",
    name="USA Tech 100",
    currency="USD",
    asset_class=AssetClass.EQUITY,  # Clean categorization for portfolio tracking
    exchange="OTC",
    underlying_instrument_id="inst_fut_ndx_20260617",  # Points to the Future!
    leverage=Decimal("20.0"),  # 1:20 Leverage
)

transaction_t212_index_cfd = Transaction(
    id="tr_t212_50250923830",
    correlation_id=None,
    asset_account_id="a_acc_001",
    timestamp=datetime(2026, 6, 11, 11, 9, 24),
    type=TransactionType.BUY,
    instrument_id="inst_cfd_t212_tech100_m26",  # Links to the corrected instrument
    quantity=Decimal("0.1"),
    price=Decimal("28829.67"),
    fee=Decimal("0.00"),
    tax=Decimal("0.00"),
    currency="USD",
    cash_impact=Decimal("0.00"),
)
