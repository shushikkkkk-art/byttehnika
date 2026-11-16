from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Role(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)
    role = db.relationship('Role')


class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False)


class Manufacturer(db.Model):
    __tablename__ = 'manufacturers'
    manufacturer_id = db.Column(db.Integer, primary_key=True)
    manufacturer_name = db.Column(db.String(100), unique=True, nullable=False)


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    supplier_id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(150), unique=True, nullable=False)


class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(20), default='шт')
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Integer, default=0)
    stock_qty = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'))
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('manufacturers.manufacturer_id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'))

    supplier = db.relationship('Supplier')
    manufacturer = db.relationship('Manufacturer')
    category = db.relationship('Category')

    @property
    def final_price(self):
        return round(float(self.price) * (1 - self.discount / 100), 2)

    @property
    def row_class(self):
        if self.stock_qty == 0:
            return "row-out-of-stock"
        if self.discount > 15:
            return "row-big-discount"
        return ""


class PickupPoint(db.Model):
    __tablename__ = 'pickup_points'
    pickup_point_id = db.Column(db.Integer, primary_key=True)
    postal_code = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(255), nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.Integer, unique=True, nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    delivery_date = db.Column(db.Date)
    pickup_point_id = db.Column(db.Integer, db.ForeignKey('pickup_points.pickup_point_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    status = db.Column(db.String(30), default='В обработке')

    pickup_point = db.relationship('PickupPoint')
    user = db.relationship('User')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='RESTRICT'))
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship('Product')