from sqlalchemy import create_engine
import os

# Allow overriding via environment variables; fall back to defaults
elite_engine = create_engine(os.getenv("ELITE_DB_URL", "postgresql://postgres:postgres@localhost:5434/fab_elite"))
corporateengine = create_engine(os.getenv("CORP_DB_URL", "postgresql://postgres:postgres@localhost:5434/fab_corporate"))
wealth_engine = create_engine(os.getenv("WEALTH_DB_URL", "postgresql://postgres:postgres@localhost:5434/fab_wealth"))
