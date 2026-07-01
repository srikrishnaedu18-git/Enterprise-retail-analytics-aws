"""
Enterprise Retail Analytics — Transaction Microservice
=======================================================
Production-grade FastAPI backend for ingesting and querying
point-of-sale transactions against an Amazon RDS instance.
"""

import os
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, status, Depends  # 🔌 Added Depends here
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Index,
    create_engine,
    desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# Database configuration — FIX: Sourced cleanly for PostgreSQL
# ---------------------------------------------------------------------------
DB_HOST = os.environ.get("DB_HOST", "")
DB_USER = os.environ.get("DB_USER", "postgres")        # 🔄 Changed fallback default to postgres
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")
DB_NAME = os.environ.get("DB_NAME", "retail_analytics")
DB_PORT = os.environ.get("DB_PORT", "5432")            # 🔄 Changed default port to 5432
DB_DRIVER = os.environ.get("DB_DRIVER", "postgresql+psycopg2") # 🔄 Changed driver to postgresql+psycopg2

# Local dev: fall back to SQLite when no DB_HOST is configured
if DB_HOST and DB_HOST != "your-rds-endpoint.amazonaws.com":
    DATABASE_URL = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
else:
    _db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retail_analytics.db")
    DATABASE_URL = f"sqlite:///{_db_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    print(f"⚡ Local dev mode — using SQLite at {_db_path}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Transaction(Base):
    """Represents a single point-of-sale transaction row."""

    __tablename__ = "transactions"

    transaction_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(64), nullable=False, index=True)
    product_id = Column(String(64), nullable=False)
    store_id = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    date = Column(
        String(32),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    __table_args__ = (
        Index("ix_transactions_date", "date"),
    )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Retail Transaction Service",
    version="1.0.0",
    description="Accepts and serves retail point-of-sale transactions.",
)

# ---------------------------------------------------------------------------
# Startup database readiness helpers
# ---------------------------------------------------------------------------

def wait_for_db(host, user, password, dbname, port, retries=5, delay=3):
    """Gracefully wait for PostgreSQL to accept connections before continuing."""
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                dbname=dbname,
                port=port,
                connect_timeout=3, # ⏱️ Avoid hanging forever if the network firewall blocks us
            )
            conn.close()
            return True
        except psycopg2.OperationalError as exc:
            print(f"Database connection attempt {attempt} failed: {exc}")
            if attempt < retries:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
    return False


@app.on_event("startup")
def startup_event():
    """Wait for the configured database to become reachable and initialize tables."""
    if DB_HOST and DB_HOST != "your-rds-endpoint.amazonaws.com":
        if not wait_for_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, int(DB_PORT)):
            raise RuntimeError("Could not connect to the database after multiple retries.")

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Pydantic schemas for request / response validation
# ---------------------------------------------------------------------------

class TransactionCreate(BaseModel):
    """Inbound payload schema for creating a new transaction."""

    transaction_id: Optional[str] = Field(
        default=None,
        description="Optional UUID — auto-generated when omitted.",
    )
    customer_id: str = Field(..., min_length=1, max_length=64)
    product_id: str = Field(..., min_length=1, max_length=64)
    store_id: str = Field(..., min_length=1, max_length=64)
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    date: Optional[str] = None

    @field_validator("transaction_id", mode="before")
    @classmethod
    def _default_uuid(cls, v):
        return v or str(uuid.uuid4())

    @field_validator("date", mode="before")
    @classmethod
    def _default_date(cls, v):
        return v or datetime.now(timezone.utc).isoformat()


class TransactionResponse(BaseModel):
    """Outbound schema returned to clients."""

    transaction_id: str
    customer_id: str
    product_id: str
    store_id: str
    quantity: int
    price: float
    date: str

    model_config = {"from_attributes": True}


# CORS — allow all origins so the React SPA on port 3000 (or any IP) can talk
# to this backend running on port 8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Dependency that yields a database session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints — FIX: Using the session dependency injections natively
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
def health_check():
    """Simple health probe for ALB / container orchestrators."""
    return {"status": "healthy"}


@app.post(
    "/api/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    """Validate, persist, and return a new transaction record."""
    try:
        row = Transaction(
            transaction_id=payload.transaction_id,
            customer_id=payload.customer_id,
            product_id=payload.product_id,
            store_id=payload.store_id,
            quantity=payload.quantity,
            price=payload.price,
            date=payload.date,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit transaction: {exc}",
        )


@app.get(
    "/api/transactions",
    response_model=List[TransactionResponse],
    tags=["transactions"],
)
def list_transactions(db: Session = Depends(get_db)):
    """Return the latest 50 transactions ordered by date descending."""
    rows = (
        db.query(Transaction)
        .order_by(desc(Transaction.date))
        .limit(50)
        .all()
    )
    return rows


# ---------------------------------------------------------------------------
# Entrypoint (for local dev — production uses the Dockerfile CMD)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)