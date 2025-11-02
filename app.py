# app.py
from flask import Flask, render_template, request, jsonify, send_file
from ipos.db import init_db, db
from model import Category, Product, Customer, Sale, SaleItem
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
import os
from werkzeug.utils import secure_filename
import io
import xlsxwriter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

init_db(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================================
# DASHBOARD
# ========================================
@app.route('/')
def index():
    total_sales = db.session.query(func.sum(Sale.total)).scalar() or 0
    total_customers = Customer.query.count()
    products_sold = db.session.query(func.sum(SaleItem.quantity)).scalar() or 0

    this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_month = db.session.query(func.sum(Sale.total))\
        .filter(Sale.date >= this_month).scalar() or 0

    qty_sum = func.coalesce(func.sum(SaleItem.quantity), 0).label('qty')
    top_product = db.session.query(Product.name, qty_sum)\
        .join(SaleItem, isouter=True)\
        .group_by(Product.id)\
        .order_by(qty_sum.desc())\
        .first()
    top_product_name = top_product.name if top_product else "N/A"

    today = datetime.now()
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)

    sales_last_week = db.session.query(func.sum(Sale.total))\
        .filter(Sale.date >= last_week_start, Sale.date <= last_week_end).scalar() or 0
    sales_this_week = db.session.query(func.sum(Sale.total))\
        .filter(Sale.date >= this_week_start).scalar() or 0

    growth = 0
    if sales_last_week > 0:
        growth = round(((sales_this_week - sales_last_week) / sales_last_week) * 100, 1)

    new_customers = db.session.query(Customer.id).join(Sale)\
        .filter(Sale.date >= this_week_start).distinct().count()

    return render_template('index.html',
        total_sales=total_sales,
        total_customers=total_customers,
        products_sold=products_sold,
        revenue_month=revenue_month,
        top_product_name=top_product_name,
        growth=growth,
        new_customers=new_customers
    )


# ========================================
# CATEGORIES
# ========================================
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


# ========================================
# PRODUCTS
# ========================================
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


# ========================================
# CUSTOMERS
# ========================================
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


# ========================================
# SALES & BILLING – FIXED: STOCK DEDUCTED
# ========================================
@app.route('/billing')
def billing():
    return render_template('billing.html')

@app.route('/api/sales', methods=['GET', 'POST'])
def api_sales():
    if request.method == 'POST':
        data = request.json
        customer_id = data.get('customer_id')
        items = data.get('items', [])
        if not items:
            return jsonify({"error": "No items"}), 400

        total = 0
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({"error": "Product not found"}), 400
            if product.stock < item['quantity']:
                return jsonify({"error": f"Only {product.stock} {product.name} in stock"}), 400
            total += product.price * item['quantity']
            product.stock -= item['quantity']  # DEDUCT STOCK

        sale = Sale(
            customer_id=customer_id,
            total=total,
            date=datetime.utcnow()
        )
        db.session.add(sale)
        db.session.flush()

        for item in items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(sale_item)

        db.session.commit()
        return jsonify({"id": sale.id, "total": total}), 201

    # GET: return all sales
    try:
        sales = Sale.query.options(
            joinedload(Sale.customer),
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).order_by(Sale.date.desc()).all()

        return jsonify([{
            "id": s.id,
            "date": s.date.strftime("%Y-%m-%d %H:%M:%S"),
            "total": float(s.total),
            "customer_id": s.customer.id if s.customer else None,
            "customer_name": s.customer.name if s.customer else "Walk-in",
            "items": [{
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.price)
            } for item in s.items]
        } for s in sales])
    
    except Exception as e:
        print("API SALES ERROR:", e)
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/sales/<int:id>')
def api_sale(id):
    sale = Sale.query.get_or_404(id)
    return jsonify(sale.to_dict())

@app.route('/sales')
def sales():
    query = Sale.query.options(
        joinedload(Sale.items).joinedload(SaleItem.product),
        joinedload(Sale.customer)
    )

    search = request.args.get('q')
    if search:
        search = search.strip()
        try:
            order_id = int(search)
            query = query.filter(Sale.id == order_id)
        except ValueError:
            query = query.join(Sale.customer).filter(
                Customer.name.ilike(f'%{search}%')
            )

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        query = query.filter(Sale.date >= start_date)
    if end_date:
        query = query.filter(Sale.date <= end_date + " 23:59:59")

    sales = query.order_by(Sale.date.desc()).all()
    sales_list = [s.to_dict() for s in sales]
    total_income = sum(s.get('total', 0) for s in sales_list)

    return render_template(
        'sales.html',
        sales=sales_list,
        total_income=total_income,
        start_date=start_date or '',
        end_date=end_date or '',
        search_query=search or ''
    )

@app.route('/sale/<int:id>')
def sale_detail(id):
    sale = Sale.query.get_or_404(id)
    return render_template('sale_detail.html', sale=sale)

@app.route('/receipt/<int:sid>')
def receipt(sid):
    sale = Sale.query.options(
        db.joinedload(Sale.items).joinedload(SaleItem.product),
        db.joinedload(Sale.customer)
    ).get_or_404(sid)
    return render_template('receipt.html', sale=sale)


# ========================================
# REPORTS & EXPORT
# ========================================
@app.route('/reports')
def reports():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    product_id = request.args.get('product_id')

    query = Sale.query.options(db.joinedload(Sale.items).joinedload(SaleItem.product))
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

@app.route('/export_excel')
def export_excel():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    product_id = request.args.get('product_id')

    query = Sale.query.options(db.joinedload(Sale.items).joinedload(SaleItem.product))
    if from_date:
        query = query.filter(Sale.date >= from_date)
    if to_date:
        query = query.filter(Sale.date <= to_date + " 23:59:59")
    if product_id:
        query = query.filter(Sale.items.any(SaleItem.product_id == int(product_id)))
    sales = query.order_by(Sale.date.desc()).all()

    rows = []
    for sale in sales:
        for item in sale.items:
            rows.append({
                'date': sale.date.strftime('%Y-%m-%d'),
                'product': item.product.name,
                'customer': sale.customer.name if sale.customer else 'Walk-in',
                'quantity': item.quantity,
                'total': item.quantity * item.price
            })

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Sales Report')

    bold = workbook.add_format({'bold': True, 'bg_color': '#E0F7FA'})
    money = workbook.add_format({'num_format': '$#,##0.00'})

    headers = ['Date', 'Product', 'Customer', 'Quantity', 'Total']
    for col, h in enumerate(headers):
        worksheet.write(0, col, h, bold)

    for r, row in enumerate(rows, start=1):
        worksheet.write(r, 0, row['date'])
        worksheet.write(r, 1, row['product'])
        worksheet.write(r, 2, row['customer'])
        worksheet.write(r, 3, row['quantity'])
        worksheet.write(r, 4, row['total'], money)

    total_income = sum(row['total'] for row in rows)
    worksheet.write(r + 2, 3, 'Total Income:', bold)
    worksheet.write(r + 2, 4, total_income, money)

    workbook.close()
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"sales_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)