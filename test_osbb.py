import psycopg
from tabulate import tabulate

DSN = "postgresql://osbb_admin:osbb_password@localhost:5432/osbb_db"

try:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.number, o.full_name, a.area, a.rooms, a.entrance, a.has_debt 
                FROM apartments a
                JOIN owners o ON a.owner_id = o.id;
            """)
            rows = cur.fetchall()
            headers = ["Номер кв.", "Власник", "Площа", "Кімнат", "Під'їзд", "Борг"]
            print("\n=== РЕЗУЛЬТАТ ПЕРЕВІРКИ БАЗИ ДАНИХ ОССБ (50+ ЗАПИСІВ) ===")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
except Exception as e:
    print("Помилка:", e)
