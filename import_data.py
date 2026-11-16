import pandas as pd
import psycopg2
from werkzeug.security import generate_password_hash
from pathlib import Path

BASE = Path("imports/14_БытТехника")

conn = psycopg2.connect(
    dbname="byttehnika",
    user="postgres",
    password="123",       
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# 1. Роли
for r in ["Гость", "АвторизованныйКлиент", "Менеджер", "Администратор"]:
    cur.execute("INSERT INTO roles(role_name) VALUES (%s) ON CONFLICT DO NOTHING", (r,))

# 2. Пользователи (кроме гостя)
users_df = pd.read_excel(BASE / "users.xlsx")
for _, row in users_df.iterrows():
    if pd.isna(row["Логин"]) or row["Роль"] == "Гость":
        continue
    role = str(row["Роль"]).strip()
    if role == "АвторизованныйКлиент":
        role = "АвторизованныйКлиент"
    cur.execute("""
        INSERT INTO users(full_name, login, password_hash, role_id)
        VALUES (%s, %s, %s, (SELECT role_id FROM roles WHERE role_name=%s))
    """, (row["ФИО"], row["Логин"],
          generate_password_hash(str(row["Пароль"])), role))

# 3. Справочники
prod_df = pd.read_excel(BASE / "products.xlsx")
for col, table, name in [
    ("Поставщик", "suppliers", "supplier_name"),
    ("Производитель", "manufacturers", "manufacturer_name"),
    ("Категория", "categories", "category_name"),
]:
    for v in prod_df[col].dropna().unique():
        cur.execute(f"INSERT INTO {table}({name}) VALUES (%s) ON CONFLICT DO NOTHING", (v,))

# 4. Товары
for _, row in prod_df.iterrows():
    img = str(row["Изображение"]).split("/")[-1]
    cur.execute("""
        INSERT INTO products(article, name, unit, price, supplier_id, manufacturer_id,
                             category_id, discount, stock_qty, description, image_path)
        VALUES (%s,%s,%s,%s,
                (SELECT supplier_id FROM suppliers WHERE supplier_name=%s),
                (SELECT manufacturer_id FROM manufacturers WHERE manufacturer_name=%s),
                (SELECT category_id FROM categories WHERE category_name=%s),
                %s,%s,%s,%s)
    """, (str(int(row["Артикул"])), row["Наименование"], row["Ед.измерения"], float(row["Цена"]),
          row["Поставщик"], row["Производитель"], row["Категория"],
          int(row["Действующая скидка"]), int(row["Количество на складе"]),
          row["Описание товара"], "static/images/products/" + img))

# 5. Пункты выдачи
pp_df = pd.read_excel(BASE / "pickup_points.xlsx")
for _, row in pp_df.iterrows():
    cur.execute("INSERT INTO pickup_points(postal_code, address) VALUES (%s,%s)",
                (str(row["Почтовый индекс"]), row["Адрес"]))

# 6. Заказы
orders_df = pd.read_excel(BASE / "orders.xlsx")
for _, row in orders_df.iterrows():
    cur.execute("""
        INSERT INTO orders(order_number, order_date, delivery_date, pickup_point_id, user_id)
        VALUES (%s,%s,%s,%s,
                (SELECT user_id FROM users WHERE full_name=%s))
    """, (int(row["Номер"]), row["Дата заказа"], row["Дата поставки"],
          int(row["Пункт выдачи (ID)"]), row["ФИО клиента"]))

conn.commit()
cur.close()
conn.close()
print("Импорт завершён успешно")