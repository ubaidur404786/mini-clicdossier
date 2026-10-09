import re
from datetime import date

from pydantic import BaseModel, Field, ValidationError, field_validator

# a monthly salary or a bill above this is surely a reading error
MAX_AMOUNT = 100000


def iban_ok(iban):
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", iban):
        return False
    # move the first 4 chars to the end, letters become numbers (A=10 ... Z=35)
    moved = iban[4:] + iban[:4]
    digits = "".join(str(int(c, 36)) for c in moved)
    return int(digits) % 97 == 1


# None is allowed everywhere: a missing value is not a wrong value
class Person(BaseModel):
    last_name: str | None = None
    first_name: str | None = None

    @field_validator("last_name")
    @classmethod
    def upper_last_name(cls, value):
        return value.upper() if value else value


class IdCard(Person):
    birth_date: date | None = None
    id_number: str | None = Field(None, pattern=r"^[A-Z0-9]{9}$")
    expiry_date: date | None = None


class Payslip(Person):
    employer: str | None = None
    pay_period: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    gross_salary: float | None = Field(None, gt=0, lt=MAX_AMOUNT)
    net_salary: float | None = Field(None, gt=0, lt=MAX_AMOUNT)


class Address(Person):
    address_line: str | None = None
    postal_code: str | None = Field(None, pattern=r"^\d{5}$")
    city: str | None = None


class ProofOfAddress(Address):
    supplier: str | None = None
    issue_date: date | None = None
    amount_due: float | None = Field(None, gt=0, lt=MAX_AMOUNT)


class BankStatement(Address):
    iban: str | None = None
    statement_date: date | None = None
    salary_credit: float | None = Field(None, gt=0, lt=MAX_AMOUNT)

    @field_validator("iban")
    @classmethod
    def check_iban(cls, value):
        if value is None:
            return value
        value = "".join(value.split()).upper()
        if not iban_ok(value):
            raise ValueError("bad iban checksum")
        return value


SCHEMAS = {
    "id_card": IdCard,
    "payslip": Payslip,
    "proof_of_address": ProofOfAddress,
    "bank_statement": BankStatement,
}


def validate(doc_type, fields):
    if doc_type not in SCHEMAS:
        return {"fields": fields, "errors": []}
    schema = SCHEMAS[doc_type]
    # small models sometimes answer "" instead of null
    fields = {name: (None if value == "" else value) for name, value in fields.items()}
    errors = []
    try:
        clean = schema(**fields)
    except ValidationError as e:
        # a wrong value becomes None, so later checks don't use it
        for err in e.errors():
            name = err["loc"][0]
            errors.append({"field": name, "value": fields.get(name), "problem": err["msg"]})
            fields[name] = None
        clean = schema(**fields)
    return {"fields": clean.model_dump(mode="json"), "errors": errors}