import uuid
from decimal import Decimal
from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str


class AccountOut(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class BalanceOut(BaseModel):
    account_id: uuid.UUID
    balance: Decimal


class TransferCreate(BaseModel):
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal


class TransferOut(BaseModel):
    id: uuid.UUID
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal
    status: str

    class Config:
        from_attributes = True