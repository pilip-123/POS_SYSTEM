# app.py
from flask import Flask, render_template, request, jsonify
from ipos.db import init_db, db
from model import Category, Product, Customer, Sale, SaleItem
from datetime import datetime
from sqlalchemy import func
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
init_db(app)

# Upload config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/categories')
def categories():
    return render_template('categories.html')

@app.route('/api/categories', methods=['GET', 'POST'])
def api_categories():
    if request.method == 'POST':
        data = request.json
        cat = Category(name=data['name'])
        db.session.add(cat)
        db.session.commit()
        return jsonify(cat.to_dict()), 201
    return jsonify([c.to_dict() for c in Category.query.all()])

@app.route('/api/categories/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_category(id):
    cat = Category.query.get_or_404(id)
    if request.method == 'PUT':
        cat.name = request.json.get('name', cat.name)
        db.session.commit()
        return jsonify(cat.to_dict())
    elif request.method == 'DELETE':
        db.session.delete(cat)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    return jsonify(cat.to_dict())

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    if request.method == 'POST':
        data = request.form.to_dict()
        file = request.files.get('image')

        image_filename = None
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f"product_{int(datetime.utcnow().timestamp())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(file_path)
            image_filename = unique_name

        prod = Product(
            name=data['name'],
            price=float(data['price']),
            stock=int(data.get('stock', 0)),
            description=data.get('description', ''),
            image=image_filename,
            category_id=data.get('category_id') or None
        )
        db.session.add(prod)
        db.session.commit()
        return jsonify(prod.to_dict()), 201

    return jsonify([p.to_dict() for p in Product.query.all()])

@app.route('/api/products/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_product(id):
    prod = Product.query.get_or_404(id)
    if request.method == 'PUT':
        data = request.form.to_dict()
        file = request.files.get('image')

        if file and file.filename and allowed_file(file.filename):
            if prod.image:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], prod.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(file.filename)
            unique_name = f"product_{int(datetime.utcnow().timestamp())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(file_path)
            prod.image = unique_name
        elif 'clear_image' in data:
            if prod.image:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], prod.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            prod.image = None

        prod.name = data.get('name', prod.name)
        prod.price = float(data.get('price', prod.price))
        prod.stock = int(data.get('stock', prod.stock))
        prod.description = data.get('description', prod.description)
        prod.category_id = data.get('category_id', prod.category_id) or None
        db.session.commit()
        return jsonify(prod.to_dict())

    elif request.method == 'DELETE':
        if prod.image:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], prod.image)
            if os.path.exists(img_path):
                os.remove(img_path)
        db.session.delete(prod)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    return jsonify(prod.to_dict())

@app.route('/customers')
def customers():
    return render_template('customers.html')

@app.route('/api/customers', methods=['GET', 'POST'])
def api_customers():
    if request.method == 'POST':
        data = request.json
        cust = Customer(name=data['name'], email=data.get('email'), phone=data.get('phone'))
        db.session.add(cust)
        db.session.commit()
        return jsonify(cust.to_dict()), 201
    return jsonify([c.to_dict() for c in Customer.query.all()])

@app.route('/api/customers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_customer(id):
    cust = Customer.query.get_or_404(id)
    if request.method == 'PUT':
        data = request.json
        cust.name = data.get('name', cust.name)
        cust.email = data.get('email', cust.email)
        cust.phone = data.get('phone', cust.phone)
        db.session.commit()
        return jsonify(cust.to_dict())
    elif request.method == 'DELETE':
        db.session.delete(cust)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    return jsonify(cust.to_dict())

@app.route('/billing')
def billing():
    return render_template('billing.html')

@app.route('/api/sales', methods=['POST'])
def api_sales():
    data = request.json
    customer_id = data.get('customer_id') or None
    items = data.get('items', [])
    if not items:
        return jsonify({"error": "Cart empty"}), 400

    sale = Sale(customer_id=customer_id)
    db.session.add(sale)
    db.session.flush()

    total = 0
    for item in items:
        prod = Product.query.get(item['product_id'])
        qty = item['qty']
        if not prod or prod.stock < qty:
            db.session.rollback()
            return jsonify({"error": "Insufficient stock"}), 400
        sale_item = SaleItem(sale_id=sale.id, product_id=prod.id, quantity=qty, price=prod.price)
        db.session.add(sale_item)
        prod.stock -= qty
        total += prod.price * qty
    sale.total = total
    db.session.commit()
    return jsonify({"id": sale.id}), 201

@app.route('/api/sales/<int:id>')
def api_sale(id):
    sale = Sale.query.get_or_404(id)
    return jsonify(sale.to_dict())

@app.route('/sales')
def sales():
    sales = Sale.query.order_by(Sale.date.desc()).all()  # ← FIXED: 'order_byナ' → 'order_by'
    sales_list = [s.to_dict() for s in sales]
    return render_template('sales.html', sales=sales_list)

@app.route('/sale/<int:id>')
def sale_detail(id):
    sale = Sale.query.get_or_404(id)
    return render_template('sale_detail.html', sale=sale)

@app.route('/receipt/<int:sid>')
def receipt(sid):
    sale = Sale.query.get_or_404(sid)
    return render_template('receipt.html', sale=sale.to_dict())

@app.route('/reports')
def reports():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    product_id = request.args.get('product_id')

    query = Sale.query
    if from_date:
        query = query.filter(Sale.date >= from_date)
    if to_date:
        query = query.filter(Sale.date <= to_date + " 23:59:59")
    sales = query.order_by(Sale.date.desc()).all()
    sales_list = [s.to_dict() for s in sales]
    total_income = sum(sale.get('total', 0) for sale in sales_list)

    prod_query = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_qty'),
        func.sum(SaleItem.quantity * SaleItem.price).label('total_sales')
    ).join(SaleItem).join(Sale)

    if from_date:
        prod_query = prod_query.filter(Sale.date >= from_date)
    if to_date:
        prod_query = prod_query.filter(Sale.date <= to_date + " 23:59:59")
    if product_id:
        prod_query = prod_query.filter(Product.id == product_id)

    product_sales = prod_query.group_by(Product.id).all()

    return render_template(
        'reports.html',
        sales=sales_list,
        total_income=total_income,
        product_sales=product_sales,
        products=Product.query.all(),
        from_date=from_date,
        to_date=to_date,
        selected_product=product_id
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)