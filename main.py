import re
from abc import ABC, abstractmethod

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel, field_validator

app = FastAPI(title="Система керування ОСББ - Інтерфейс API", version="0.1.0")

DSN = "postgresql://osbb_admin:osbb_password@localhost:5432/osbb_db"
PHONE_REGEX = r"^\+380\d{9}$"
APT_NUMBER_REGEX = (
    r"^\d{1,4}[а-яА-Яa-zA-Z]?$"  # Валідація номера квартири (цифри + літера)
)


# =====================================================================
# СХЕМИ ВАЛІДАЦІЇ PYDANTIC & REGEX (Пункти 5.b та 6.b)
# =====================================================================
class ApartmentCreate(BaseModel):
    number: str
    owner_name: str
    owner_phone: str
    area: float
    rooms: int
    entrance: str
    has_debt: bool

    @field_validator("number")
    def validate_number(cls, v):
        if not re.match(APT_NUMBER_REGEX, v):
            raise ValueError(
                "Номер квартири має містити 1-4 цифри та опціонально одну літеру"
            )
        return v

    @field_validator("entrance")
    def validate_entrance(cls, v):
        if v not in ["перший", "другий", "третій"]:
            raise ValueError("Під'їзд має бути: 'перший', 'другий' або 'третій'")
        return v

    @field_validator("owner_phone")
    def validate_phone(cls, v):
        if not re.match(PHONE_REGEX, v):
            raise ValueError("Номер телефону має бути у форматі +380XXXXXXXXX")
        return v


# =====================================================================
# OPEN/CLOSED PRINCIPLE (OCP) - АБСТРАКЦІЯ СХОВИЩА (Пункти 7, 10)
# =====================================================================
class ApartmentRepository(ABC):
    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def get_by_id(self, apt_id: int):
        pass

    @abstractmethod
    def create(self, apt: ApartmentCreate):
        pass

    @abstractmethod
    def update(self, apt_id: int, apt: ApartmentCreate):
        pass

    @abstractmethod
    def delete(self, apt_id: int):
        pass


class PostgresApartmentRepository(ApartmentRepository):
    def get_all(self):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            return conn.execute("""
                SELECT a.id, a.number, o.full_name as owner_name, o.phone as owner_phone, 
                       a.area, a.rooms, a.entrance, a.has_debt 
                FROM apartments a
                JOIN owners o ON a.owner_id = o.id
                ORDER BY a.id DESC;
            """).fetchall()

    def get_by_id(self, apt_id: int):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            return conn.execute(
                """
                SELECT a.id, a.number, o.full_name as owner_name, o.phone as owner_phone, 
                       a.area, a.rooms, a.entrance, a.has_debt 
                FROM apartments a
                JOIN owners o ON a.owner_id = o.id
                WHERE a.id = %s;
            """,
                (apt_id,),
            ).fetchone()

    def create(self, apt: ApartmentCreate):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            # Спочатку створюємо або знаходимо власника
            owner = conn.execute(
                "INSERT INTO owners (full_name, phone) VALUES (%s, %s) RETURNING id;",
                (apt.owner_name, apt.owner_phone),
            ).fetchone()
            owner_id = owner["id"]

            # Створюємо квартиру
            new_apt = conn.execute(
                """
                INSERT INTO apartments (number, owner_id, area, rooms, entrance, has_debt)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, number, area, rooms, entrance, has_debt;
            """,
                (apt.number, owner_id, apt.area, apt.rooms, apt.entrance, apt.has_debt),
            ).fetchone()

            return new_apt

    def update(self, apt_id: int, apt: ApartmentCreate):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            # Перевіримо чи є квартира
            existing = conn.execute(
                "SELECT owner_id FROM apartments WHERE id = %s", (apt_id,)
            ).fetchone()
            if not existing:
                return None
            owner_id = existing["owner_id"]

            # Оновлюємо дані власника
            conn.execute(
                "UPDATE owners SET full_name = %s, phone = %s WHERE id = %s",
                (apt.owner_name, apt.owner_phone, owner_id),
            )
            # Оновлюємо дані квартири
            updated = conn.execute(
                """
                UPDATE apartments 
                SET number = %s, area = %s, rooms = %s, entrance = %s, has_debt = %s 
                WHERE id = %s 
                RETURNING id, number, area, rooms, entrance, has_debt;
            """,
                (apt.number, apt.area, apt.rooms, apt.entrance, apt.has_debt, apt_id),
            ).fetchone()

            return updated

    def delete(self, apt_id: int):
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            return conn.execute(
                "DELETE FROM apartments WHERE id = %s RETURNING id", (apt_id,)
            ).fetchone()


# Ініціалізація репозиторію
repo = PostgresApartmentRepository()


# =====================================================================
# REST API МАРШРУТИ (Пункти 5.a, 6.b)
# =====================================================================
@app.get("/apartments")
def get_all_apartments():
    return repo.get_all()


@app.get("/apartments/{apt_id}")
def get_apartment(apt_id: int):
    apt = repo.get_by_id(apt_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Квартиру не знайдено")
    return apt


@app.post("/apartments", status_code=201)
def create_apartment(apt: ApartmentCreate):
    new_apt = repo.create(apt)
    return {"message": "Квартиру успішно додано до бази даних", "data": new_apt}


@app.put("/apartments/{apt_id}")
def update_apartment(apt_id: int, apt: ApartmentCreate):
    updated_apt = repo.update(apt_id, apt)
    if not updated_apt:
        raise HTTPException(
            status_code=404, detail="Квартиру не знайдено для оновлення"
        )
    return {"message": "Дані квартири успішно оновлено", "data": updated_apt}


@app.delete("/apartments/{apt_id}")
def delete_apartment(apt_id: int):
    deleted = repo.delete(apt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Квартиру не знайдено")
    return {"message": f"Квартиру з ID {apt_id} успішно видалено з бази даних"}
