import random
import psycopg

DSN = "postgresql://osbb_admin:osbb_password@localhost:5432/osbb_db"


def init_db():
    print("Підключення до бази ОСББ")
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # 1. Створення таблиць
            cur.execute("""
                CREATE TABLE IF NOT EXISTS owners (
                    id SERIAL PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS apartments (
                    id SERIAL PRIMARY KEY,
                    number TEXT NOT NULL,
                    owner_id INTEGER REFERENCES owners(id) ON DELETE CASCADE,
                    area NUMERIC(5,2) NOT NULL,
                    rooms INTEGER NOT NULL,
                    entrance TEXT NOT NULL,
                    has_debt BOOLEAN NOT NULL
                );
            """)

            cur.execute("TRUNCATE apartments, owners RESTART IDENTITY CASCADE;")

            # 2. Генерація власників
            surnames = [
                "Ферстаппен",
                "Шевченко",
                "Хемілтон",
                "Козак",
                "Кеннеді",
                "Редфілд",
                "Антонеллі",
                "Поліщук",
            ]
            names = [
                "Макс",
                "Олена",
                "Кімі",
                "Марія",
                "Л'юіс",
                "Наталія",
                "Леон",
                "Тетяна",
            ]

            print("Генерація власників та 52 квартир для ОСББ...")
            entrances = ["перший", "другий", "третій"]

            owner_ids = []
            for _ in range(20):  # Створимо 20 реальних власників
                owner_name = f"{random.choice(surnames)} {random.choice(names)}"
                phone = f"+38050{random.randint(1000000, 9999999)}"
                cur.execute(
                    "INSERT INTO owners (full_name, phone) VALUES (%s, %s) RETURNING id;",
                    (owner_name, phone),
                )
                owner_ids.append(cur.fetchone()[0])

            # Генерація рівно 52 квартир згідно вимог методички
            for apt_counter in range(1, 53):
                apt_number = f"{apt_counter}"
                owner_id = random.choice(owner_ids)
                area = round(random.uniform(35.0, 110.0), 1)
                rooms = random.choice([1, 2, 3, 4])
                entrance = random.choice(entrances)
                has_debt = random.choice([True, False])

                cur.execute(
                    """
                    INSERT INTO apartments (number, owner_id, area, rooms, entrance, has_debt)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """,
                    (apt_number, owner_id, area, rooms, entrance, has_debt),
                )

        print("Успішно створено та заповнено 52 записи квартир.")


if __name__ == "__main__":
    init_db()