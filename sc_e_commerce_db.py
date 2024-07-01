from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy import select, delete 
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate, ValidationError
from typing import List
import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+mysqlconnector://root:***********@localhost/sc_e_commerce_db_2"
app.json.sort_keys = False

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)


# Table Creation
class Customer(Base):
    __tablename__ ="Customers"
    customer_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(300))
    birthday: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    email: Mapped[str] = mapped_column(db.String(320))
    phone: Mapped[str] = mapped_column(db.String(15))
    customer_account: Mapped["CustomerAccount"] = db.relationship(back_populates="customer")    
    orders: Mapped[List["Order"]] = db.relationship(back_populates="customer")

class CustomerAccount(Base):
    __tablename__ = "Customer_Accounts"
    account_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    username: Mapped[str] = mapped_column(db.String(300), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(350), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))
    customer: Mapped["Customer"] = db.relationship(back_populates="customer_account")

order_product = db.Table(
    "Order_Product",
    Base.metadata,
    db.Column("order_id", db.ForeignKey("Orders.order_id"), primary_key=True),
    db.Column("product_id", db.ForeignKey("Products.product_id"), primary_key=True)
)

class Product(Base):
    __tablename__ = "Products"
    product_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(300), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)

class Order(Base):
    __tablename__ = "Orders"
    order_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('Customers.customer_id'))
    customer: Mapped["Customer"] = db.relationship(back_populates="orders")
    products: Mapped[List["Product"]] = db.relationship(secondary=order_product)

class Review(Base):
    __tablename__ ="Reviews"
    review_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    product_id: Mapped[int] = mapped_column(db.ForeignKey('Products.product_id'), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('Customer.customer_id'), nullable=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    rating: Mapped[int] = mapped_column(db.Integer(), nullable=False)
    review: Mapped[str] = mapped_column(db.String(3000), nullable=True)
    
with app.app_context():
    db.create_all()

# Customer CRUD
class CustomerSchema(ma.Schema):
    customer_id = fields.Integer(required=False)
    name = fields.String(required=True)
    birthday = fields.Date(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)
        
    class Meta:
        fields = ("customer_id", "name", "birthday", "email", "phone")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

@app.route("/")
def home():
    return "Star Citizen E-Commerce"

@app.route("/customers", methods=["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    try:
        with Session(db.engine) as session:
            with session.begin():
                name = customer_data['name']
                birthday = customer_data['birthday']
                email = customer_data['email']
                phone = customer_data['phone']
                new_customer = Customer(name=name, birthday=birthday, email=email, phone=phone)
                session.add(new_customer)
                session.commit()
            return jsonify({"message": "New customer added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customers", methods=["GET"])
def get_customer():
    try:
        query = select(Customer)
        result = db.session.execute(query).scalars()
        customers = result.all()
        return customers_schema.jsonify(customers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customer/by-name", methods=["GET"])
def get_customer_by_name():
    try:
        name = request.args.get("name")
        search = f"%{name}%" 
        query = select(Customer).where(Customer.name.like(search)).order_by(Customer.name.asc())
        customer = db.session.execute(query).scalars().all()
        return customers_schema.jsonify(customer)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/customers/<int:customer_id>', methods=["PUT"])
def update_customer(customer_id):
    try:
        with Session(db.engine) as session:
            with session.begin():
                query = select(Customer).filter(Customer.customer_id == customer_id)
                result = session.execute(query).scalars().first()
                if result is None:
                    return jsonify({"error": "Customer not found"}), 404
                customer = result
                try:
                    customer_data = customer_schema.load(request.json)
                except ValidationError as err:
                    return jsonify(err.messages), 400
                for field, value in customer_data.items():
                    setattr(customer, field, value)
                session.commit()
                return jsonify({"message": "Customer details updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/customers/<int:customer_id>', methods=["DELETE"])
def delete_customer(customer_id):
    try:
        delete_statement = delete(Customer).where(Customer.customer_id == customer_id)
        with db.session.begin():
            result = db.session.execute(delete_statement)
            if result.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404
            return jsonify({"message": "Customer removed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # Customer Account Schema
class CustomerAccountSchema(ma.Schema):
    account_id = fields.Integer(required=False)
    username = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, validate=validate.Length(min=1))
    customer_id = fields.Integer(required=True)
    customer = fields.Nested(CustomerSchema, required=True)

    class Meta:
        fields = ("account_id", "username", "password", "customer_id", "customer")

customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)

# Customer Account CRUD (Might not work)
@app.route('/customer_account', methods=["POST"])
def add_customer_account():
    try:
        customer_account_data = customer_account_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    try:
        with Session(db.engine) as session:
            with session.begin():
                new_customer_account = CustomerAccount(**customer_account_data)
                session.add(new_customer_account)
                session.commit()
        return jsonify({"message": "Customer account successfully created!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/customer_accounts', methods=["GET"])
def get_customer_accounts():
    try:
        query = select(CustomerAccount)
        result = db.session.execute(query).scalars()
        customer_accounts = result.all()
        return customer_accounts_schema.jsonify(customer_accounts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customer_accounts/by-username", methods=["GET"])
def get_customer_account_by_username():
    try:
        username = request.args.get("username")
        search = f"%{username}%" 
        query = select(CustomerAccount).where(CustomerAccount.username.like(search)).order_by(CustomerAccount.username.asc())
        customer_accounts = db.session.execute(query).scalars().all()
        return customer_accounts_schema.jsonify(customer_accounts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/customer_accounts/<int:account_id>', methods=["PUT"])
def update_customer_account(account_id):
    try:
        with Session(db.engine) as session:
            with session.begin():
                query = select(CustomerAccount).filter(CustomerAccount.account_id == account_id)
                result = session.execute(query).scalars().first()
                if result is None:
                    return jsonify({"error": "Customer account not found"}), 404
                customer_account = result
                try:
                    customer_account_data = customer_account_schema.load(request.json)
                except ValidationError as err:
                    return jsonify(err.messages), 400
                for field, value in customer_account_data.items():
                    setattr(customer_account, field, value)
                session.commit
            return jsonify({"message": "Product details updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/customer_accounts/<int:account_id>', methods=["DELETE"])
def delete_customer_account(account_id):
    try:
        delete_statement = delete(CustomerAccount).where(CustomerAccount.account_id == account_id)
        with db.session.begin():
            result = db.session.execute(delete_statement)
            if result.rowcount == 0:
                return jsonify({"error": "Customer account not found"}), 404
            return jsonify({"message": "Customer account removed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500   


# Product Schema
class ProductSchema(ma.Schema):
    product_id = fields.Integer(required=False)
    name = fields.String(required=True, validate=validate.Length(min=1))
    price = fields.Float(requires=True, validate= validate.Range(min=0))

    class Meta:
        fields = ("product_id", "name", "price")
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# Product API Routes
@app.route("/products", methods = ["POST"])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    with Session(db.engine)as session:
        with session.begin():
            name = product_data['name']
            price = product_data['price']
            new_product = Product(name = name, price = price)
            session.add(new_product)
            session.commit()
    return jsonify({"message": "New product successfully added"}), 201

@app.route("/products", methods = ["GET"])
def get_products():
    query = select(Product)
    result = db.session.execute(query).scalars()
    products = result.all()
    return products_schema.jsonify(products)

@app.route("/products/by-name", methods=["GET"])
def get_product_by_name():
    name = request.args.get("name")
    search = f"%{name}%" 
    query = select(Product).where(Product.name.like(search)).order_by(Product.price.asc())
    products = db.session.execute(query).scalars().all()
    return products_schema.jsonify(products)

@app.route("/products/<int:product_id>", methods = ["PUT"])
def updated_product(product_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Product).filter(Product.product_id == product_id)
            result = session.execute(query).scalars().first()
            if result is None:
                return jsonify({"error": "Product not found"}), 404
            product = result
            try:
                product_data = product_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400
            for field, value in product_data.items():
                setattr(product,field,value)
            session.commit()
            return jsonify({"message": "Product details updated successfully!"}), 200

@app.route("/products/<int:product_id>", methods = ["DELETE"])
def delete_product(product_id):
    delete_statement = delete(Product).where(Product.product_id==product_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        return jsonify({"message": "Product successfully deleted!"}), 200
# Order Schema
class OrderSchema(ma.Schema):
    order_id = fields.Integer(required=False)
    date = fields.Date(required=True)
    customer_id = fields.Integer(required=True)
    product_id = fields.List(fields.Integer())

    class Meta:
        fields = ("order_id", "date", "customer_id", "product_id")  
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# Order API Routes
@app.route('/orders', methods=["POST"])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    with Session(db.engine) as session:
        new_order = Order(customer_id= order_data['customer_id'], date = order_data['date'])
        session.add(new_order)
        session.commit()
    return jsonify({"message": "New order successfully added!"}), 201

@app.route("/orders", methods=["GET"])
def get_orders():
    query = select(Order)
    result = db.session.execute(query).scalars()
    return orders_schema.jsonify(result)

@app.route("/orders/by-order_id", methods=["GET"])
def get_orders_by_name():
    order = request.args.get("order_id")
    search = f"%{order}%" 
    query = select(Order).where(Order.order_id.like(search)).order_by(Order.order_id.asc())
    orders = db.session.execute(query).scalars().all()
    return orders_schema.jsonify(orders)

@app.route('/orders/<int:order_id>', methods=["PUT"])
def update_order(order_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Order).filter(Order.order_id==order_id)
            result = session.execute(query).scalar() #first result object
            if result is None:
                return jsonify({"message": "Product Not Found"}), 404
            order = result
            try:
                order_data = order_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400
            
            for field, value in order_data.items():
                setattr(order, field, value)
            session.commit()
            return jsonify({"Message": "Order was successfully updated! "}), 200

@app.route("/orders/<int:order_id>", methods = ["DELETE"])
def delete_order(order_id):
    delete_statement = delete(Order).where(Order.order_id==order_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": "Order not found" }), 404
        return jsonify({"message": "Order removed successfully"}), 200    
    
# Review Schema
class ReviewSchema(ma.Schema):
    review_id = fields.Integer(required=False)
    product_id = fields.Integer(required=True)
    customer_id = fields.Integer(required=False)
    date = fields.Date(required=True)
    rating = fields.Integer(required=True, validate=validate.Range(min=1, max=5))
    review = fields.String(required=False)

    class Meta:
        fields = ("review_id", "product_id", "customer_id", "date", "rating", "review")

review_schema = ReviewSchema
reviews_schema = ReviewSchema(many=True)

# Review API Routes, Will only have POST, GET, DELETE (no updating reviews once posted, BE ABOUT IT!)
@app.route('/reviews/', methods = ["POST"])
def add_review():
  try:
    
    review_data = review_schema.load(request.json)
  except ValidationError as err:
    return jsonify(err.messages), 400
  with Session(db.engine)as session:
    with session.begin():
      product_id = review_data["product_id"]
      customer_id = review_data["customer_id"]
      date = review_data["date"]
      rating = review_data["rating"]
      review = review_data["review"]
      new_review = Review(product_id=product_id, customer_id=customer_id, date=date, rating=rating, review=review)
      session.add(new_review)
      session.commit()
  return jsonify({"message": "New review successfully added"}), 201

@app.route("/reviews", methods=["GET"])
def get_reviews():
    query = select(Review)
    result = db.session.execute(query).scalars()
    return reviews_schema.jsonify(result)

@app.route("/reviews/by-product_id", methods=["GET"])
def get_reviews_by_id():
    review = request.args.get("product_id")
    search = f"%{review}%" 
    query = select(Review).where(Review.product_id.like(search)).order_by(Review.product_id.asc())
    reviews = db.session.execute(query).scalars().all()
    return reviews_schema.jsonify(reviews)

@app.route("/reviews/<int:review_id>", methods = ["DELETE"])
def delete_review(review_id):
    delete_statement = delete(Review).where(Review.review_id==review_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": "Order not found" }), 404
        return jsonify({"message": "Review removed successfully"}), 200   

if __name__ == "__main__":
    app.run(debug=True)