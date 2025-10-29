# model.py
from ipos.db import db
from datetime import datetime


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))  # filename only
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='products')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
            "description": self.description or "",
            "image": self.image,
            "image_url": f"/static/uploads/{self.image}"
                         if self.image else "/static/no-image.png",
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "None"
        }


class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email or "",
            "phone": self.phone or ""
        }


class Sale(db.Model):
    __tablename__ = 'sale'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)
    customer = db.relationship('Customer', backref='sales')
    items = db.relationship('SaleItem', backref='sale', lazy=True)

    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "date": self.date.isoformat(),
            "total": self.total,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else "Guest"
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items]
        return data


class SaleItem(db.Model):
    __tablename__ = 'sale_item'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            "product_name": self.product.name,
            "quantity": self.quantity,
            "price": self.price,
            "subtotal": round(self.quantity * self.price, 2)
        }

    def __repr__(self):
        return f"<SaleItem {self.product.name} x{self.quantity}>"