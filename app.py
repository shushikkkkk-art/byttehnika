from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from pathlib import Path
from uuid import uuid4
from PIL import Image
from models import (db, User, Product, Category, Manufacturer, Supplier,
                    Order, PickupPoint)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:123@localhost:5432/byttehnika'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret-key-change-me'
db.init_app(app)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_ = request.form.get('login', '').strip()
        pwd = request.form.get('password', '')
        user = User.query.filter_by(login=login_).first()
        if user and check_password_hash(user.password_hash, pwd):
            session['user_id'] = user.user_id
            session['role'] = user.role.role_name
            session['full_name'] = user.full_name
            return redirect(url_for('products'))
        flash('Неверный логин или пароль. Проверьте раскладку и Caps Lock.', 'error')
    return render_template('login.html')


@app.route('/guest')
def guest():
    session.clear()
    session['role'] = 'Гость'
    return redirect(url_for('products'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/products')
def products():
    role = session.get('role')
    if not role:
        return redirect(url_for('login'))

    query = Product.query
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', '')
    supplier_id = request.args.get('supplier', type=int)

    if role in ('Менеджер', 'Администратор', 'АвторизованныйКлиент') and search:
        like = f'%{search}%'
        query = query.filter(db.or_(
            Product.name.ilike(like),
            Product.description.ilike(like),
            Product.article.ilike(like),
            Product.unit.ilike(like),
        ))

    if role in ('Менеджер', 'Администратор') and supplier_id:
        query = query.filter(Product.supplier_id == supplier_id)

    if role in ('Менеджер', 'Администратор'):
        if sort == 'asc':
            query = query.order_by(Product.stock_qty.asc())
        elif sort == 'desc':
            query = query.order_by(Product.stock_qty.desc())

    products = query.all()
    suppliers = Supplier.query.all()
    return render_template('products.html', products=products,
                           suppliers=suppliers, search=search,
                           sort=sort, supplier_id=supplier_id)


@app.route('/admin/product/new', methods=['GET', 'POST'])
@app.route('/admin/product/<int:pid>/edit', methods=['GET', 'POST'])
def product_form(pid=None):
    if session.get('role') != 'Администратор':
        flash('Доступ только администратору.', 'error')
        return redirect(url_for('products'))
    if pid is None and session.get('editing_product'):
        flash('Уже открыто окно редактирования. Закройте его сначала.', 'warning')
        return redirect(url_for('products'))
    product = Product.query.get(pid) if pid else None

    if request.method == 'POST':
        try:
            price = float(request.form['price'])
            stock = int(request.form['stock_qty'])
            discount = int(request.form['discount'])
        except ValueError:
            flash('Цена/количество/скидка должны быть числами.', 'error')
            return render_template('product_form.html', product=product,
                                   categories=Category.query.all(),
                                   manufacturers=Manufacturer.query.all(),
                                   suppliers=Supplier.query.all())

        if price < 0 or stock < 0 or not (0 <= discount <= 100):
            flash('Недопустимые значения: цена и количество ≥ 0, скидка 0–100.', 'error')
            return render_template('product_form.html', product=product,
                                   categories=Category.query.all(),
                                   manufacturers=Manufacturer.query.all(),
                                   suppliers=Supplier.query.all())

        image_path = product.image_path if product else None
        file = request.files.get('image')
        if file and file.filename:
            filename = f"{uuid4().hex}.jpg"
            save_path = Path('static/images/products') / filename
            img = Image.open(file).convert('RGB').resize((300, 200), Image.LANCZOS)
            img.save(save_path, 'JPEG')
            if product and product.image_path:
                old = Path(product.image_path)
                if old.exists():
                    old.unlink()
            image_path = str(save_path).replace('\\', '/')

        data = dict(
            name=request.form['name'],
            price=price,
            unit=request.form['unit'],
            stock_qty=stock,
            discount=discount,
            description=request.form['description'],
            supplier_id=int(request.form['supplier_id']),
            manufacturer_id=int(request.form['manufacturer_id']),
            category_id=int(request.form['category_id']),
            image_path=image_path,
        )
        if product:
            for k, v in data.items():
                setattr(product, k, v)
            flash('Товар обновлён.', 'info')
        else:
            article = request.form.get('article') or str(uuid4().hex[:8])
            db.session.add(Product(article=article, **data))
            flash('Товар добавлен.', 'info')
        db.session.commit()
        session.pop('editing_product', None)
        return redirect(url_for('products'))

    if pid:
        session['editing_product'] = pid
    return render_template('product_form.html', product=product,
                           categories=Category.query.all(),
                           manufacturers=Manufacturer.query.all(),
                           suppliers=Supplier.query.all())


@app.route('/admin/product/<int:pid>/cancel')
def product_cancel(pid):
    session.pop('editing_product', None)
    return redirect(url_for('products'))


@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
def product_delete(pid):
    if session.get('role') != 'Администратор':
        flash('Доступ запрещён.', 'error')
        return redirect(url_for('products'))
    product = Product.query.get_or_404(pid)
    from models import OrderItem
    if OrderItem.query.filter_by(product_id=pid).first():
        flash('Нельзя удалить товар: он присутствует в заказах.', 'error')
        return redirect(url_for('products'))
    if product.image_path and Path(product.image_path).exists():
        Path(product.image_path).unlink()
    db.session.delete(product)
    db.session.commit()
    flash('Товар удалён.', 'info')
    return redirect(url_for('products'))


@app.route('/orders')
def orders():
    if session.get('role') not in ('Менеджер', 'Администратор'):
        flash('Доступ только менеджеру и администратору.', 'error')
        return redirect(url_for('products'))
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('orders.html', orders=orders)


if __name__ == '__main__':
    app.run(debug=True)