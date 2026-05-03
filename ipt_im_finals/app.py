import os
import re
import json
from datetime import datetime
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import NotFound, MethodNotAllowed
from jinja2 import Environment, FileSystemLoader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.serving import run_simple
from werkzeug.utils import redirect, secure_filename
from urllib.parse import quote_plus, quote
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, or_, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_URL = ""
basedir = os.path.abspath(os.path.dirname(__file__))
DB_URL = "sqlite:///" + os.path.join(basedir, "anik_shop.db")

Base = declarative_base()

class Product(Base):
    __tablename__ = 'product'
    id = Column("product_id", Integer, primary_key=True)
    name = Column(String)
    brand = Column(String, default="")
    price = Column("selling_price", Float)
    stock = Column("stock_qty", Integer)
    image = Column("image_file", String)
    category = Column(String, default="")
    category_id = Column(Integer)
    supplier_id = Column(Integer)
    sku = Column(String(50), default="")
    barcode = Column(String(50), default="")
    cost_price = Column(Float, default=0.0)
    reorder_level = Column(Integer, default=0)
    unit = Column(String(20), default="")
    status = Column(String(20), default="active")

class Cart_Item(Base):
    __tablename__ = 'cart_item'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)

class Pos_Cart_Item(Base):
    __tablename__ = 'pos_cart_item'
    id = Column(Integer, primary_key=True)
    cashier_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)

class Sale_Item(Base):
    __tablename__ = 'sale_item'
    id = Column("sale_item_id", Integer, primary_key=True)
    sale_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

class Purchase_Order(Base):
    __tablename__ = 'purchase_order'
    id = Column("po_id", Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    supplier_id = Column(Integer, nullable=False)
    order_date = Column(String(30), default="")
    received_date = Column(String(30), default="")
    total_cost = Column(Float, default=0.0)
    status = Column(String(20), default="pending")

class Po_Item(Base):
    __tablename__ = 'po_item'
    id = Column("po_item_id", Integer, primary_key=True)
    po_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    qty_ordered = Column(Integer, default=0)
    qty_received = Column(Integer, default=0)
    unit_cost = Column(Float, default=0.0)

class Stock_Movement(Base):
    __tablename__ = 'stock_movement'
    id = Column("movement_id", Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    cashier_id = Column(Integer, nullable=False)
    type = Column(String(20), default="")
    quantity = Column(Integer, default=0)
    reason = Column(String, default="")
    moved_at = Column(String(30), default="")

class User(Base):
    __tablename__ = 'user'
    id = Column("user_id", Integer, primary_key=True)
    first_name = Column(String) 
    last_name = Column(String)   
    email = Column(String, unique=True)
    phone = Column(String)
    password = Column(String)
    role = Column(String)       
    loyalty_points = Column(Integer, default=0)

class Category(Base):
    __tablename__ = 'category'
    id = Column("category_id", Integer, primary_key=True)
    name = Column(String(100), default="")
    description = Column(String, default="")

class Supplier(Base):
    __tablename__ = 'supplier'
    id = Column("supplier_id", Integer, primary_key=True)
    name = Column(String(100), default="")
    contact_person = Column(String(100), default="")
    phone = Column(String(30), default="")
    email = Column(String(100), default="")
    street = Column(String)
    city = Column(String)
    zip_code = Column(String)

class Admin(Base):
    __tablename__ = 'admin'
    id = Column("admin_id", Integer, primary_key=True)
    first_name = Column(String(50)) 
    last_name = Column(String(50))  
    username = Column(String(50), unique=True)
    password_hash = Column(String(120))
    email = Column(String(100), unique=True)
    role = Column(String(30), default="admin")
    status = Column(String(20), default="active")

class Discount(Base):
    __tablename__ = 'discount'
    id = Column("discount_id", Integer, primary_key=True)
    name = Column(String(100), default="")
    type = Column(String(50), default="")
    value = Column(Float, default=0.0)
    valid_from = Column(String(30), default="")
    valid_until = Column(String(30), default="")
    applies_to = Column(String(100), default="")
    status = Column(String(20), default="active")

class Sale(Base):
    __tablename__ = 'sale'
    id = Column("sale_id", Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    customer_id = Column(Integer, nullable=False)
    discount_id = Column(Integer, nullable=True)
    total_amount = Column(Float, default=0.0)
    sale_date = Column(String(30), default="")
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    payment_method = Column(String(50), default="Cash on Delivery")
    amount_tendered = Column(Float, default=0.0)
    change_given = Column(Float, default=0.0)
    status = Column(String(20), default="Placed")
    delivery_street = Column(String, default="")
    delivery_city = Column(String, default="")
    delivery_zip = Column(String, default="")

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

SessionProd = Session
SessionUser = Session

Base.metadata.create_all(engine)

env = Environment(loader=FileSystemLoader("templates"))

def admin_cancel_sale(request, sale_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    
    db_session = SessionProd()
    try:
        sale = db_session.query(Sale).filter_by(id=sale_id).first()
        if not sale or sale.status == "Cancelled":
            return redirect_admin_dashboard(request, panel_default="sales-panel", msg="Cannot cancel this sale")

        sale_items = db_session.query(Sale_Item).filter_by(sale_id=sale_id).all()
        
        moved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in sale_items:
            product = db_session.query(Product).filter_by(id=item.product_id).first()
            if product:
                product.stock = (product.stock or 0) + item.quantity
                
                db_session.add(Stock_Movement(
                    product_id=product.id,
                    cashier_id=user_id,
                    type="IN",
                    quantity=item.quantity,
                    reason=f"Restored from Cancelled Sale #{sale.id}",
                    moved_at=moved_at
                ))

        sale.status = "Cancelled"
        db_session.commit()
        msg = "Sale cancelled and stock restored"
    finally:
        db_session.close()
        
    return redirect_admin_dashboard(request, panel_default="sales-panel", msg=msg)

def ensure_user_schema():
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(customer)")
        cols = [row[1] for row in cur.fetchall()]
        
        if "password" not in cols:
            cur.execute("ALTER TABLE customer ADD COLUMN password TEXT")
        if "is_admin" not in cols:
            cur.execute("ALTER TABLE customer ADD COLUMN is_admin INTEGER DEFAULT 0")
        if "linked_staff_id" not in cols:
            cur.execute("ALTER TABLE customer ADD COLUMN linked_staff_id INTEGER")
        conn.commit()
    finally:
        conn.close()

def ensure_sale_schema():
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(sale)")
        cols = [row[1] for row in cur.fetchall()]

        if not cols:
            return

        missing_column_sql = {
            "subtotal": "ALTER TABLE sale ADD COLUMN subtotal FLOAT DEFAULT 0.0",
            "discount_amount": "ALTER TABLE sale ADD COLUMN discount_amount FLOAT DEFAULT 0.0",
            "tax_amount": "ALTER TABLE sale ADD COLUMN tax_amount FLOAT DEFAULT 0.0",
            "payment_method": "ALTER TABLE sale ADD COLUMN payment_method TEXT DEFAULT 'Cash on Delivery'",
            "amount_tendered": "ALTER TABLE sale ADD COLUMN amount_tendered FLOAT DEFAULT 0.0",
            "change_given": "ALTER TABLE sale ADD COLUMN change_given FLOAT DEFAULT 0.0",
            "status": "ALTER TABLE sale ADD COLUMN status TEXT DEFAULT 'Placed'",
            "customer_name": "ALTER TABLE sale ADD COLUMN customer_name TEXT DEFAULT ''",
            "customer_phone": "ALTER TABLE sale ADD COLUMN customer_phone TEXT DEFAULT ''",
            "delivery_address": "ALTER TABLE sale ADD COLUMN delivery_address TEXT DEFAULT ''",
        }

        for column_name, sql in missing_column_sql.items():
            if column_name not in cols:
                cur.execute(sql)

        conn.commit()
    finally:
        conn.close()

def ensure_discount_schema():
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(discount)")
        cols = [row[1] for row in cur.fetchall()]

        if not cols:
            return

        missing_column_sql = {
            "type": "ALTER TABLE discount ADD COLUMN type TEXT DEFAULT ''",
            "valid_from": "ALTER TABLE discount ADD COLUMN valid_from TEXT DEFAULT ''",
            "valid_until": "ALTER TABLE discount ADD COLUMN valid_until TEXT DEFAULT ''",
            "applies_to": "ALTER TABLE discount ADD COLUMN applies_to TEXT DEFAULT ''",
        }

        for column_name, sql in missing_column_sql.items():
            if column_name not in cols:
                cur.execute(sql)

        conn.commit()
    finally:
        conn.close()

def ensure_master_schema():
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()

        def ensure_columns(table_name, missing_column_sql):
            cur.execute(f"PRAGMA table_info({table_name})")
            cols = [row[1] for row in cur.fetchall()]
            if not cols:
                return
            for column_name, sql in missing_column_sql.items():
                if column_name not in cols:
                    cur.execute(sql)

        ensure_columns("category", {
            "description": "ALTER TABLE category ADD COLUMN description TEXT DEFAULT ''",
        })

        ensure_columns("supplier", {
            "contact_person": "ALTER TABLE supplier ADD COLUMN contact_person TEXT DEFAULT ''",
            "phone": "ALTER TABLE supplier ADD COLUMN phone TEXT DEFAULT ''",
            "email": "ALTER TABLE supplier ADD COLUMN email TEXT DEFAULT ''",
            "address": "ALTER TABLE supplier ADD COLUMN address TEXT DEFAULT ''",
        })

        ensure_columns("product", {
            "sku": "ALTER TABLE product ADD COLUMN sku TEXT DEFAULT ''",
            "barcode": "ALTER TABLE product ADD COLUMN barcode TEXT DEFAULT ''",
            "cost_price": "ALTER TABLE product ADD COLUMN cost_price FLOAT DEFAULT 0.0",
            "reorder_level": "ALTER TABLE product ADD COLUMN reorder_level INTEGER DEFAULT 0",
            "unit": "ALTER TABLE product ADD COLUMN unit TEXT DEFAULT ''",
            "status": "ALTER TABLE product ADD COLUMN status TEXT DEFAULT 'active'",
        })

        conn.commit()
    finally:
        conn.close()

#ensure_user_schema()
#ensure_sale_schema()
#ensure_discount_schema()
#ensure_master_schema()

def get_is_admin(request):
    user_id = get_user_id(request)
    if not user_id:
        return False
    
    db_session = SessionUser()
    try:
        admin_exists = db_session.query(Admin).filter_by(id=user_id).first()
        return admin_exists is not None
    finally:
        db_session.close()

def get_user_id(request):
    raw_user_id = request.args.get('user_id') or request.form.get('user_id')
    if raw_user_id is None:
        raw_user_id = request.cookies.get('user_id')
    if raw_user_id in (None, "", "None", "null", "undefined"):
        return None
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None

def redirect_admin_dashboard(request, panel_default="dashboard-panel", msg=None):
    """Return to SPA-style admin URL with session query params; keeps current panel when provided."""
    uid = get_user_id(request)
    is_admin = get_is_admin(request)
    panel = (request.args.get("panel") or request.form.get("panel") or "").strip()
    if not panel:
        panel = panel_default
    admin_q = "True" if is_admin else "False"
    uid_q = str(uid) if uid is not None else ""
    url = f"/admin_dashboard?admin={admin_q}&user_id={uid_q}&panel={quote_plus(panel)}"
    if msg:
        url += "&msg=" + quote_plus(str(msg))
    return redirect(url)

ALLOWED_SALE_TRANSITIONS = {
    "Placed": {"Processing", "Cancelled"},
    "Processing": {"Shipped", "Cancelled"},
    "Shipped": {"Delivered"},
    "Delivered": set(),
    "Cancelled": set(),
}

def can_transition_status(current_status, next_status):
    current = (current_status or "Placed").strip()
    target = (next_status or "").strip()
    if current == target:
        return True
    allowed_next = ALLOWED_SALE_TRANSITIONS.get(current, set())
    return target in allowed_next

def compute_discount_amount(discount, subtotal):
    if discount is None or subtotal <= 0:
        return 0.0
    dtype = (discount.type or "").strip().lower()
    if dtype in ("percent", "percentage"):
        pct = max(min(float(discount.value or 0), 100.0), 0.0)
        return round((subtotal * pct) / 100.0, 2)
    return round(max(float(discount.value or 0), 0.0), 2)

def compute_points_earned(total_amount):
    amount = max(float(total_amount or 0.0), 0.0)
    return int(amount // 100)

def resolve_staff_cashier_id(db_session, user_id):
    if user_id is not None:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user and user.role.lower() in ['cashier', 'admin']:
            return user.id

    active_staff = db_session.query(User).filter(User.role.ilike('cashier')).order_by(User.id.asc()).first()
    if active_staff:
        return active_staff.id
    
    any_admin = db_session.query(User).filter(User.role.ilike('admin')).order_by(User.id.asc()).first()
    return any_admin.id if any_admin else None

def resolve_default_online_cashier_id(db_session):
    staff = db_session.query(User).filter(User.role.in_(['cashier', 'admin'])).order_by(User.id.asc()).first()
    return staff.id if staff else None

def render(template, request, **context):
    user_id = get_user_id(request)
    search_term = (request.args.get('search') or '').strip()
    
    current_user_name = ""
    current_user_role = "User"
    current_loyalty_points = 0
    is_authenticated = user_id is not None
    is_admin = False
    cart_count = 0

    if user_id is not None:
        db_session = SessionUser()
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if user:
                is_admin = (user.role.lower() in ['admin', 'cashier'])
                current_loyalty_points = user.loyalty_points or 0
                current_user_name = (user.first_name or user.email.split("@")[0] or "User").strip()
                current_user_role = user.role.capitalize() if user.role else "User"
        finally:
            db_session.close()

        dbp = SessionProd()
        try:
            cart_rows = dbp.query(Cart_Item.quantity).filter_by(user_id=user_id).all()
            cart_count = sum([(row[0] or 0) for row in cart_rows])
        finally:
            dbp.close()

    context.update({
        'is_admin': is_admin,
        'user_id': str(user_id) if user_id is not None else "",
        'base_url': BASE_URL,
        'search_term': search_term,
        'current_path': request.path,
        'is_authenticated': is_authenticated,
        'current_user_name': current_user_name,
        'current_user_role': current_user_role,
        'current_loyalty_points': current_loyalty_points,
        'cart_count': cart_count
    })

    if 'session' not in context:
        context['session'] = {'user_id': user_id} if user_id is not None else {}

    return Response(env.get_template(template).render(**context), content_type="text/html")

url_map = Map([
    Rule("/", endpoint="home"),
    Rule("/products", endpoint="products"),
    Rule("/contactus", endpoint="contactus"),
    Rule("/thecompany", endpoint="thecompany"),
    Rule("/thehistory", endpoint="thehistory"),
    Rule("/services", endpoint="services"),
    Rule("/orders", endpoint="orders"),
    Rule("/admin_dashboard", endpoint="admin_dashboard"),
    Rule("/admin/sales/<int:sale_id>/status", endpoint="admin_update_sale_status", methods=["POST"]),
    Rule("/admin/pos/add/<int:product_id>", endpoint="admin_pos_add_product", methods=["POST"]),
    Rule("/admin/pos/item/<int:item_id>/update", endpoint="admin_pos_update_item", methods=["POST"]),
    Rule("/admin/pos/item/<int:item_id>/remove", endpoint="admin_pos_remove_item", methods=["POST"]),
    Rule("/admin/pos/clear", endpoint="admin_pos_clear", methods=["POST"]),
    Rule("/admin/pos/process", endpoint="admin_pos_process_sale", methods=["POST"]),
    Rule("/admin/purchase-orders/create", endpoint="admin_create_purchase_order", methods=["POST"]),
    Rule("/admin/purchase-orders/<int:po_id>/receive", endpoint="admin_receive_purchase_order", methods=["POST"]),
    Rule("/admin/customers/register", endpoint="admin_register_customer", methods=["POST"]),
    Rule("/admin_customers", endpoint="admin_customers"),
    Rule("/register", endpoint="register", methods=["GET", "POST"]),
    Rule("/login", endpoint="login", methods=["GET", "POST"]),
    Rule("/logout", endpoint="logout"),
    Rule("/add_product", endpoint="add_product", methods=["GET", "POST"]),
    Rule("/edit/<int:id>", endpoint="edit_product", methods=["GET", "POST"]),
    Rule("/delete/<int:id>", endpoint="delete_product"),
    Rule("/cart", endpoint="cart"),
    Rule("/cart/add/<int:product_id>", endpoint="add_to_cart"),
    Rule("/cart/update/<int:item_id>", endpoint="update_cart_quantity"),
    Rule("/cart/remove/<int:item_id>", endpoint="remove_from_cart"),
    Rule("/checkout", endpoint="checkout", methods=["GET", "POST"]),
    Rule("/api/dashboard/stats", endpoint="api_dashboard_stats", methods=["GET"]),
    Rule("/api/supplier-products/<int:supplier_id>", endpoint="get_supplier_products"),
    Rule("/admin/sales/<int:sale_id>/cancel", endpoint="admin_cancel_sale", methods=["POST"]),
    Rule("/api/barcode-lookup", endpoint="api_barcode_lookup"),
], strict_slashes=False)

def home(request):
    return redirect("/login")

def api_dashboard_stats(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return Response(json.dumps({"error": "Unauthorized"}), status=403, content_type="application/json")

    if request.method != "GET":
        return Response(json.dumps({"error": "Method not allowed"}), status=405, content_type="application/json")

    db = SessionProd()
    try:
        today_prefix = datetime.now().strftime("%Y-%m-%d")

        # Today's totals
        today_sales = db.query(Sale).filter(Sale.sale_date.like(f"{today_prefix}%")).all()
        today_count = len(today_sales)
        today_revenue = sum([(s.total_amount or 0.0) for s in today_sales])

        # All-time totals
        all_sales = db.query(Sale).all()
        all_count = len(all_sales)
        all_revenue = sum([(s.total_amount or 0.0) for s in all_sales])

        # Low stock products
        low_stock = db.query(Product).filter(
            Product.stock <= Product.reorder_level,
            func.lower(Product.status) == "active"
        ).all()

        # Top 5 products by units sold
        top_raw = db.query(
            Sale_Item.product_id,
            func.sum(Sale_Item.quantity).label("total_sold")
        ).group_by(Sale_Item.product_id).order_by(func.sum(Sale_Item.quantity).desc()).limit(5).all()

        payload = {
            "today": {
                "sales_count": today_count or 0,
                "total_revenue": float(today_revenue or 0),
            },
            "all_time": {
                "sales_count": all_count or 0,
                "total_revenue": float(all_revenue or 0),
            },
            "low_stock_count": len(low_stock),
            "low_stock_items": [
                {
                    "product_id": p.id,
                    "name": p.name,
                    "stock_qty": p.stock,
                    "reorder_level": p.reorder_level,
                }
                for p in low_stock
            ],
            "top_products": [
                {
                    "product_id": int(r.product_id or 0),
                    "total_sold": int(r.total_sold or 0),
                }
                for r in top_raw
            ],
        }
        return Response(json.dumps(payload), status=200, content_type="application/json")
    finally:
        db.close()

def require_admin(request):
    user_id = get_user_id(request)
    if user_id is None:
        return None, False, redirect("/login")

    dbu = SessionUser()
    try:
        u = dbu.query(User).filter_by(id=user_id).first()
        if not u or u.role.lower() not in ['admin', 'cashier']:
            return user_id, False, redirect("/products")
    finally:
        dbu.close()

    return user_id, True, None

def admin_dashboard(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return denial
    customer_search = (request.args.get("customer_search") or "").strip()
    product_search = (request.args.get("product_search") or "").strip()
    product_category = (request.args.get("product_category") or "all").strip()
    msg = (request.args.get("msg") or "").strip()

    dbp = SessionProd()
    try:
        all_products = dbp.query(Product).order_by(Product.id.desc()).all()
        product_query = dbp.query(Product)
        if product_search:
            like_term = f"%{product_search}%"
            product_query = product_query.filter(
                or_(Product.name.ilike(like_term), Product.sku.ilike(like_term))
            )
        if product_category and product_category.lower() != "all":
            product_query = product_query.filter(func.lower(Product.category) == product_category.lower())
        products = product_query.order_by(Product.id.desc()).all()
        product_categories = sorted(
            {((p.category or "").strip()) for p in all_products if (p.category or "").strip()},
            key=lambda s: s.lower()
        )
        low_stock_products = [p for p in all_products if (p.stock or 0) >= 0 and (p.stock or 0) <= 5]
        low_stock_count = len([p for p in low_stock_products if (p.stock or 0) > 0])
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        today_sales = dbp.query(Sale).filter(Sale.sale_date.like(f"{today_prefix}%")).all()
        today_transactions = len(today_sales)
        today_revenue = sum([(s.total_amount or 0.0) for s in today_sales])
        all_time_revenue = sum([(s.total_amount or 0.0) for s in dbp.query(Sale).all()])

        sale_rows = dbp.query(Sale).order_by(Sale.id.desc()).limit(15).all()
        recent_sales = []
        for sale in sale_rows:
            item_count = dbp.query(Sale_Item).filter_by(sale_id=sale.id).count()
            sale_items = dbp.query(Sale_Item, Product).join(
                Product, Sale_Item.product_id == Product.id
            ).filter(Sale_Item.sale_id == sale.id).all()
            detail_items = []
            for sale_item, product in sale_items:
                detail_items.append({
                    "name": (product.name if product else f"Product #{sale_item.product_id}"),
                    "quantity": sale_item.quantity,
                    "line_total": sale_item.line_total,
                })
            recent_sales.append({
                "sale": sale,
                "item_count": item_count,
                "detail_items": detail_items,
            })

        top_products_query = dbp.query(
            Sale_Item.product_id,
            func.sum(Sale_Item.quantity).label("units_sold")
        ).group_by(Sale_Item.product_id).order_by(func.sum(Sale_Item.quantity).desc()).limit(10).all()
        top_products = []
        for product_id, units_sold in top_products_query:
            product = dbp.query(Product).filter_by(id=product_id).first()
            top_products.append({
                "product_id": product_id,
                "product_name": (product.name if product else f"Product #{product_id}"),
                "units_sold": int(units_sold or 0)
            })

        stock_rows = dbp.query(Stock_Movement, Product).join(
            Product, Stock_Movement.product_id == Product.id
        ).order_by(Stock_Movement.id.desc()).limit(20).all()
        stock_movements = []
        for movement, product in stock_rows:
            stock_movements.append({
                "movement": movement,
                "product_name": (product.name if product else f"Product #{movement.product_id}")
            })

        po_rows = dbp.query(Purchase_Order).order_by(Purchase_Order.id.desc()).limit(20).all()
        supplier_rows = dbp.query(Supplier).order_by(Supplier.name.asc()).all()
        suppliers = [{"id": s.id, "name": s.name} for s in supplier_rows]
        purchase_orders = []
        for po in po_rows:
            supplier = dbp.query(Supplier).filter_by(id=po.supplier_id).first()
            item_count = dbp.query(Po_Item).filter_by(po_id=po.id).count()
            purchase_orders.append({
                "po": po,
                "supplier_id": (supplier.id if supplier else f"Supplier #{po.supplier_id}"),
                "item_count": item_count,
            })

        pos_cashier_id = resolve_staff_cashier_id(dbp, user_id)
        po_cashier_id = pos_cashier_id
        pos_rows = []
        if pos_cashier_id is not None:
            pos_rows = dbp.query(Pos_Cart_Item, Product).join(
                Product, Pos_Cart_Item.product_id == Product.id
            ).filter(Pos_Cart_Item.cashier_id == pos_cashier_id).all()

        pos_cart_items = []
        pos_subtotal = 0.0
        total_qty = 0
        
        for pos_item, product in pos_rows:
            line_total = (product.price or 0.0) * (pos_item.quantity or 0)
            pos_subtotal += line_total
            total_qty += (pos_item.quantity or 0)
            pos_cart_items.append({
                "pos_item": pos_item,
                "product": product,
                "line_total": line_total
            })

        if total_qty >= 5:
            pos_discount = 100.0
        elif total_qty >= 3:
            pos_discount = 75.0
        elif total_qty > 0:
            pos_discount = 50.0
        else:
            pos_discount = 0.0
            
        pos_total = round(pos_subtotal - pos_discount, 2)
        pos_tax = round(pos_total - (pos_total / 1.12), 2)
        pos_net_subtotal = round(pos_total - pos_tax, 2)
            
    finally:
        dbp.close()

    dbu2 = SessionUser()
    try:
        customer_query = dbu2.query(User).filter(User.role != 'admin').order_by(User.id.asc())
        all_customers = customer_query.all()
        customer_total = len(all_customers)
        customers = all_customers

        total_loyalty_points = sum(int(c.loyalty_points or 0) for c in all_customers)
        average_points = (total_loyalty_points / customer_total) if customer_total else 0
        top_customer = max(all_customers, key=lambda c: int(c.loyalty_points or 0), default=None)

        top_customers_sorted = sorted(
            all_customers,
            key=lambda c: int(c.loyalty_points or 0),
            reverse=True
        )[:5]
        points_bands = {"0-50": 0, "51-150": 0, "151-300": 0, "301+": 0}
        for c in all_customers:
            pts = int(c.loyalty_points or 0)
            if pts <= 50:
                points_bands["0-50"] += 1
            elif pts <= 150:
                points_bands["51-150"] += 1
            elif pts <= 300:
                points_bands["151-300"] += 1
            else:
                points_bands["301+"] += 1

        customer_graph_data = {
            "totals": {
                "total_customers": customer_total,
                "total_points": total_loyalty_points,
                "average_points": round(average_points, 1),
                "top_customer_points": int(top_customer.loyalty_points or 0) if top_customer else 0,
            },
            "top_customers": {
                "labels": [c.first_name for c in top_customers_sorted],
                "values": [int(c.loyalty_points or 0) for c in top_customers_sorted],
            },
            "top_customers_details": [
                {
                    "id": int(c.id or 0),
                    "name": c.first_name,
                    "email": c.email,
                    "phone": c.phone,
                    "points": int(c.loyalty_points or 0),
                }
                for c in top_customers_sorted
            ],
            "distribution": {
                "labels": list(points_bands.keys()),
                "values": list(points_bands.values()),
            },
        }
    finally:
        dbu2.close()

    return render(
        "admin/admin_dashboard.html",
        request,
        title="Admin Dashboard",
        admin_view="dashboard",
        stats={
            "today_transactions": today_transactions,
            "low_stock_count": low_stock_count,
            "today_revenue": today_revenue,
            "all_time_revenue": all_time_revenue,
        },
        products=products,
        all_products=all_products,
        low_stock_products=low_stock_products[:8],
        recent_sales=recent_sales,
        top_products=top_products,
        stock_movements=stock_movements,
        purchase_orders=purchase_orders,
        suppliers=suppliers,
        po_cashier_id=po_cashier_id,
        pos_cart_items=pos_cart_items,
        pos_subtotal=pos_subtotal,
        pos_tax=pos_tax,         
        pos_discount=pos_discount, 
        pos_total=pos_total,   
        pos_cashier_id=pos_cashier_id,
        customers=customers,
        customer_total=customer_total,
        customer_graph_data=json.dumps(customer_graph_data),
        customer_search=customer_search,
        product_search=product_search,
        product_category=product_category,
        product_categories=product_categories,
        pos_net_subtotal=pos_net_subtotal,
        msg=msg,
    )

def admin_create_purchase_order(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return denial

    supplier_id = (request.form.get("supplier_id") or "").strip()
    product_ids_raw = request.form.getlist("product_id[]")
    qtys_raw = request.form.getlist("qty_ordered[]")
    costs_raw = request.form.getlist("unit_cost[]")
    if not product_ids_raw:
        product_ids_raw = [request.form.get("product_id")]
        qtys_raw = [request.form.get("qty_ordered")]
        costs_raw = [request.form.get("unit_cost")]

    panel = (request.args.get("panel") or "purchase-panel").strip()
    if not supplier_id:
        return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Fill+all+PO+fields")
    po_items_payload = []
    for idx in range(max(len(product_ids_raw), len(qtys_raw), len(costs_raw))):
        product_id_raw = ((product_ids_raw[idx] if idx < len(product_ids_raw) else "") or "").strip()
        qty_ordered_raw = ((qtys_raw[idx] if idx < len(qtys_raw) else "") or "").strip()
        unit_cost_raw = ((costs_raw[idx] if idx < len(costs_raw) else "") or "").strip()
        if not product_id_raw and not qty_ordered_raw and not unit_cost_raw:
            continue
        try:
            product_id = int(product_id_raw)
            qty_ordered = int(qty_ordered_raw)
            unit_cost = float(unit_cost_raw)
        except ValueError:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Invalid+PO+values")
        if qty_ordered <= 0 or unit_cost < 0:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=PO+quantity/cost+is+invalid")
        po_items_payload.append({
            "product_id": product_id,
            "qty_ordered": qty_ordered,
            "unit_cost": unit_cost,
        })
    if not po_items_payload:
        return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Add+at+least+one+PO+item")

    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        if cashier_id is None:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=No+valid+staff+cashier+record")

        supplier = db_session.query(Supplier).filter_by(id=supplier_id).first()
        
        if supplier is None:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Supplier+not+found")

        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_cost = round(sum([item["qty_ordered"] * item["unit_cost"] for item in po_items_payload]), 2)
        
        po = Purchase_Order(
            supplier_id=supplier.id,
            user_id=cashier_id, # Changed from cashier_id to user_id
            order_date=order_date,
            total_cost=total_cost,
            status="pending"
        )
        db_session.add(po)
        db_session.flush()

        for payload in po_items_payload:
            db_session.add(Po_Item(
                po_id=po.id,
                product_id=payload["product_id"],
                qty_ordered=payload["qty_ordered"],
                qty_received=0,
                unit_cost=payload["unit_cost"]
            ))
        db_session.commit()
    finally:
        db_session.close()

    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Purchase+order+created")

def get_supplier_products(request, supplier_id):
    db_session = SessionProd()
    try:
        prods = db_session.query(Product).filter_by(supplier_id=supplier_id).all()
        product_list = [
            {"id": p.id, "name": p.name, "cost": p.cost_price or 0.0} 
            for p in prods
        ]
        return Response(json.dumps(product_list), status=200, content_type="application/json")
    finally:
        db_session.close()

def admin_receive_purchase_order(request, po_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return denial

    panel = (request.args.get("panel") or "purchase-panel").strip()
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        po = db_session.query(Purchase_Order).filter_by(id=po_id).first()
        if po is None:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=PO+not+found")

        po_items = db_session.query(Po_Item).filter_by(po_id=po.id).all()
        moved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in po_items:
            remaining = max((item.qty_ordered or 0) - (item.qty_received or 0), 0)
            if remaining <= 0:
                continue
            product = db_session.query(Product).filter_by(id=item.product_id).first()
            if product:
                product.stock = (product.stock or 0) + remaining
                item.qty_received = (item.qty_received or 0) + remaining
                db_session.add(Stock_Movement(
                    product_id=product.id,
                    cashier_id=cashier_id,
                    type="IN",
                    quantity=remaining,
                    reason=f"PO #{po.id} received",
                    moved_at=moved_at
                ))
        po.received_date = moved_at
        po.status = "received"
        db_session.commit()
    finally:
        db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=PO+received")

def admin_update_sale_status(request, sale_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return denial

    panel = (request.args.get("panel") or "sales-panel").strip()
    next_status = (request.form.get("status") or "").strip()
    db_session = SessionProd()
    try:
        sale = db_session.query(Sale).filter_by(id=sale_id).first()
        if sale and can_transition_status(sale.status, next_status):
            sale.status = next_status
            db_session.commit()
            msg = "Order+status+updated"
        else:
            msg = "Invalid+transition"
    finally:
        db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg={msg}")

def admin_pos_add_product(request, product_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    panel = (request.args.get("panel") or "pos-panel").strip()
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        product = db_session.query(Product).filter_by(id=product_id).first()
        if product and (product.stock or 0) > 0:
            existing = db_session.query(Pos_Cart_Item).filter_by(cashier_id=cashier_id, product_id=product_id).first()
            if existing: existing.quantity += 1
            else: db_session.add(Pos_Cart_Item(cashier_id=cashier_id, product_id=product_id, quantity=1))
            db_session.commit()
            msg = "Added+to+POS"
        else: msg = "Out+of+stock"
    finally: db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg={msg}")

def admin_pos_update_item(request, item_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    action = (request.form.get("action") or "").strip().lower()
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        item = db_session.query(Pos_Cart_Item).filter_by(id=item_id, cashier_id=cashier_id).first()
        if item:
            if action == "inc": item.quantity += 1
            elif action == "dec":
                item.quantity -= 1
                if item.quantity <= 0: db_session.delete(item)
            db_session.commit()
    finally: db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel=pos-panel")

def admin_pos_remove_item(request, item_id):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        item = db_session.query(Pos_Cart_Item).filter_by(id=item_id, cashier_id=cashier_id).first()
        if item:
            db_session.delete(item)
            db_session.commit()
    finally: db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel=pos-panel")

def admin_pos_clear(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        db_session.query(Pos_Cart_Item).filter_by(cashier_id=cashier_id).delete()
        db_session.commit()
    finally: db_session.close()
    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel=pos-panel")

def admin_pos_process_sale(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    cust_id = int(request.form.get("customer_id") or 0)
    try:
        tendered_raw = request.form.get("amount_tendered") or "0"
        amount_tendered = float(str(tendered_raw).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        amount_tendered = 0.0

    base_pos_url = f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel=pos-panel"
    db_session = SessionProd()
    try:
        cashier_id = resolve_staff_cashier_id(db_session, user_id)
        rows = db_session.query(Pos_Cart_Item, Product).join(
            Product, Pos_Cart_Item.product_id == Product.id
        ).filter(Pos_Cart_Item.cashier_id == cashier_id).all()
        if not rows:
            return redirect(base_pos_url + "&msg=Cart+empty")

        # Calculate Sticker Total and Item Count
        sticker_subtotal = round(sum([(float(p.price or 0) * int(item.quantity or 0)) for item, p in rows]), 2)
        total_qty = sum([int(item.quantity or 0) for item, product in rows])

        # Automated Discount Logic
        if total_qty >= 5:
            disc_amt = 100.0
        elif total_qty >= 3:
            disc_amt = 75.0
        elif total_qty > 0:
            disc_amt = 50.0
        else:
            disc_amt = 0.0

        final_total = round(sticker_subtotal - disc_amt, 2)
        tax_amount = round(final_total - (final_total / 1.12), 2)
        subtotal = round(final_total - tax_amount, 2)
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sale = Sale(
            user_id=cashier_id,
            customer_id=cust_id,
            sale_date=sale_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=disc_amt,
            total_amount=final_total,
            status="Completed"
        )

        db_session.add(sale)
        db_session.flush()
        lines_for_receipt = []
        for item, product in rows:
            lt = round(float(product.price or 0) * int(item.quantity or 0), 2)
            lines_for_receipt.append({"name": product.name or "Item", "qty": int(item.quantity or 0), "line": lt})
            db_session.add(Sale_Item(sale_id=sale.id, product_id=product.id, quantity=item.quantity, unit_price=product.price, line_total=product.price * item.quantity))
            product.stock = max(product.stock - item.quantity, 0)
            db_session.add(Stock_Movement(product_id=product.id, cashier_id=cashier_id, type="OUT", quantity=item.quantity, reason=f"POS Sale #{sale.id}", moved_at=sale_date))
            db_session.delete(item)
            
        if cust_id > 0:
            customer = db_session.query(User).filter_by(id=cust_id).first()
            if customer:
                customer.loyalty_points += compute_points_earned(final_total)
                
        db_session.commit()

        change_due = round(max(amount_tendered - final_total, 0.0), 2)
        lines_enc = quote(json.dumps(lines_for_receipt), safe="")
        return redirect(
            f"{base_pos_url}&pos_sale=1&sale_id={sale.id}&sale_date={quote_plus(sale_date)}"
            f"&total={quote_plus(f'{final_total:.2f}')}&tendered={quote_plus(f'{amount_tendered:.2f}')}"
            f"&change={quote_plus(f'{change_due:.2f}')}&lines={lines_enc}"
        )
    finally:
        db_session.close()

def admin_customers(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None: return denial
    search = (request.args.get("search") or "").strip()
    dbu = SessionUser()
    try:
        query = dbu.query(User).filter(User.role != 'admin')
        if search: query = query.filter(or_(User.first_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
        users = query.all()
    finally: dbu.close()
    return render("admin/admin_dashboard.html", request, title="Customers", admin_view="customers", customers=users, search_filter=search)

def admin_register_customer(request):
    user_id, is_admin, denial = require_admin(request)
    if denial is not None:
        return denial

    panel = (request.args.get("panel") or "customers-panel").strip()
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    email = (request.form.get("email") or "").strip()

    if not name or not email:
        return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Name+and+email+are+required")

    dbu = SessionUser()
    try:
        existing = dbu.query(User).filter_by(email=email).first()
        if existing:
            return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Email+already+exists")

        # Admin-created customers get a default password so the record is valid.
        default_password_hash = generate_password_hash("customer123")

        dbu.add(User(
            first_name=name,
            phone=phone,
            email=email,
            password=default_password_hash,
            role='customer',
        ))

        dbu.commit()
    finally:
        dbu.close()

    return redirect(f"/admin_dashboard?admin={is_admin}&user_id={user_id}&panel={panel}&msg=Customer+registered")

def login(request):
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        
        db_session = SessionUser()
        user = db_session.query(User).filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            is_admin_access = user.role.lower() in ['admin', 'cashier']
            uid = user.id
            db_session.close()

            if is_admin_access:
                target_url = f"/admin_dashboard?admin=True&user_id={uid}&panel=dashboard-panel"
            else:
                target_url = f"/products?admin=False&user_id={uid}"

            response = redirect(target_url)
            response.set_cookie("user_id", str(uid), max_age=60*60*24*7, httponly=True)
            response.set_cookie("is_admin", str(is_admin_access), max_age=60*60*24*7, httponly=True)
            return response
        else:
            if db_session: db_session.close()
            error = "Invalid email or password."
    return render("pages/auth/login.html", request, title="Login", error=error)

def products(request):
    search = (request.args.get('search') or '').strip()
    cat = (request.args.get('category') or 'all').strip()
    
    # We need to define these so the template knows what the current settings are
    filters_dict = {
        'search': search,
        'category': cat,
        'price': (request.args.get('price') or 'all').strip(),
        'sort': (request.args.get('sort') or 'name_asc').strip()
    }

    db_session = SessionProd()
    try:
        query = db_session.query(Product)
        if search: 
            query = query.filter(Product.name.ilike(f"%{search}%"))
        if cat.lower() != 'all': 
            query = query.filter(Product.category == cat)
            
        items = query.all()
        categories = [r[0] for r in db_session.query(Product.category).distinct().all() if r[0]]
    finally: 
        db_session.close()

    # Added filters=filters_dict back into the render call
    return render(
        "pages/shop/products.html", 
        request, 
        title="Products", 
        product_items=items, 
        categories=categories,
        filters=filters_dict
    )

def add_to_cart(request, product_id):
    user_id = get_user_id(request)
    if user_id is None: return redirect("/login")
    db_session = SessionProd()
    existing = db_session.query(Cart_Item).filter_by(user_id=user_id, product_id=product_id).first()
    if existing: existing.quantity += 1
    else: db_session.add(Cart_Item(user_id=user_id, product_id=product_id, quantity=1))
    db_session.commit()
    db_session.close()
    return redirect(f"/products?msg=Added&user_id={user_id}&admin={get_is_admin(request)}")

def cart(request):
    user_id = get_user_id(request)
    if user_id is None: return redirect("/login")
    db_session = SessionProd()
    rows = db_session.query(Cart_Item, Product).join(
        Product, Cart_Item.product_id == Product.id
    ).filter(Cart_Item.user_id == user_id).all()
    items = [{"item": c, "product": p, "subtotal": p.price * c.quantity} for c, p in rows]
    total = sum([i["subtotal"] for i in items])
    db_session.close()
    return render("pages/shop/cart.html", request, title="Cart", items=items, total=total)

def update_cart_quantity(request, item_id):
    user_id = get_user_id(request)
    action = request.args.get("action", "").lower()
    db_session = SessionProd()
    item = db_session.query(Cart_Item).filter_by(id=item_id, user_id=user_id).first()
    if item:
        if action == "inc": item.quantity += 1
        elif action == "dec":
            item.quantity -= 1
            if item.quantity <= 0: db_session.delete(item)
        db_session.commit()
    db_session.close()
    return redirect(f"/cart?user_id={user_id}&admin={get_is_admin(request)}")

def remove_from_cart(request, item_id):
    user_id = get_user_id(request)
    db_session = SessionProd()
    item = db_session.query(Cart_Item).filter_by(id=item_id, user_id=user_id).first()
    if item:
        db_session.delete(item)
        db_session.commit()
    db_session.close()
    return redirect(f"/cart?user_id={user_id}&admin={get_is_admin(request)}")

def checkout(request):
    user_id = get_user_id(request)
    if user_id is None: return redirect("/login")
    db_session = SessionProd()
    rows = db_session.query(Cart_Item, Product).join(
        Product, Cart_Item.product_id == Product.id
    ).filter(Cart_Item.user_id == user_id).all()
    if not rows: return redirect("/cart")
    subtotal = sum([p.price * c.quantity for c, p in rows])
    customer = db_session.query(User).filter_by(id=user_id).first()
    avail_pts = int(customer.loyalty_points or 0)
    
    error = None
    if request.method == "POST":
        pts_spend = int(request.form.get("points_to_redeem") or 0)
        final_total = max(subtotal - pts_spend, 0)
        cashier_id = resolve_default_online_cashier_id(db_session)
        created_at = datetime.now().strftime("%Y-%m-%d %I:%M %p")

        sale = Sale(
            user_id=cashier_id,
            customer_id=user_id,
            sale_date=created_at,
            subtotal=subtotal,
            discount_amount=pts_spend,
            total_amount=final_total,
            status="Placed"
        )
        
        db_session.add(sale)
        db_session.flush()
        for c, p in rows:
            db_session.add(Sale_Item(sale_id=sale.id, product_id=p.id, quantity=c.quantity, unit_price=p.price, line_total=p.price * c.quantity))
            p.stock -= c.quantity
            db_session.delete(c)
        customer.loyalty_points = max(avail_pts - pts_spend, 0) + compute_points_earned(final_total)
        db_session.commit()
        db_session.close()
        return redirect("/orders?msg=Success")
    
    db_session.close()
    return render("pages/shop/checkout.html", request, title="Checkout", subtotal=subtotal, available_points=avail_pts)

def logout(request):
    response = redirect("/")
    response.delete_cookie("user_id")
    response.delete_cookie("is_admin")
    return response

def add_product(request):
    _, is_admin, denial = require_admin(request)
    if denial: return denial
    if request.method == "POST":
        db_session = SessionProd()
        try:
            name = (request.form.get("name") or "").strip()
            brand = (request.form.get("brand") or "").strip()
            category_name = (request.form.get("category") or "").strip()
            price = float(request.form.get("price"))
            stock = int(request.form.get("stock"))
            image_file = ""

            image_upload = request.files.get("image_upload")
            if image_upload and image_upload.filename:
                upload_name = secure_filename(image_upload.filename)
                _, ext = os.path.splitext(upload_name)
                ext = ext.lower()
                if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                    return Response("Unsupported image format.", status=400)

                filename_root = secure_filename(os.path.splitext(name)[0]) or "product"
                image_file = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename_root}{ext}"
                products_dir = os.path.join(basedir, "static", "img", "products")
                os.makedirs(products_dir, exist_ok=True)
                image_upload.save(os.path.join(products_dir, image_file))

            # DB requires numeric FK columns (category_id, supplier_id). The form only
            # submits the category name, so we resolve it from the Category table.
            category = db_session.query(Category).filter_by(name=category_name).first()
            if category is None:
                category = Category(name=category_name)
                db_session.add(category)
                db_session.flush()

            category_id = category.id

            supplier_row = (
                db_session.query(Product.supplier_id)
                .filter(Product.category_id == category_id)
                .group_by(Product.supplier_id)
                .order_by(func.count(Product.supplier_id).desc())
                .first()
            )

            supplier_id = (supplier_row[0] if supplier_row and supplier_row[0] is not None else None)
            if supplier_id is None:
                first_supplier = db_session.query(Supplier).order_by(Supplier.id.asc()).first()
                supplier_id = (first_supplier.id if first_supplier else 1)

            new_p = Product(
                first_name=name,
                brand=brand,
                price=price,
                stock=stock,
                category=category_name,
                image=image_file,
                category_id=category_id,
                supplier_id=supplier_id,
                sku="",
                barcode="",
                cost_price=0.0,
                reorder_level=0,
                unit="",
                status="active",
            )
            db_session.add(new_p)
            db_session.commit()
        finally:
            db_session.close()

        return redirect_admin_dashboard(request, panel_default="products-panel")
    return render("admin/modals/add_product.html", request, title="Add Product")

def edit_product(request, id):
    _, is_admin, denial = require_admin(request)
    if denial: return denial
    db_session = SessionProd()
    product = db_session.query(Product).get(id)
    if not product:
        db_session.close()
        return redirect_admin_dashboard(request, panel_default="products-panel")
    if request.method == "POST":
        name_raw = request.form.get("name")
        price_raw = request.form.get("price")
        stock_raw = request.form.get("stock")

        if name_raw is not None and str(name_raw).strip():
            product.name = str(name_raw).strip()

        try:
            if price_raw is not None and str(price_raw).strip() != "":
                product.price = float(price_raw)
        except (TypeError, ValueError):
            pass

        try:
            if stock_raw is not None and str(stock_raw).strip() != "":
                product.stock = int(float(stock_raw))
        except (TypeError, ValueError):
            pass

        db_session.commit()
        db_session.close()
        return redirect_admin_dashboard(request, panel_default="products-panel")
    return render("admin/modals/edit_product.html", request, product=product)

def delete_product(request, id):
    _, is_admin, denial = require_admin(request)
    if denial: return denial
    db_session = SessionProd()
    p = db_session.query(Product).get(id)
    if p: db_session.delete(p)
    db_session.commit()
    db_session.close()
    return redirect_admin_dashboard(request, panel_default="products-panel")

def register(request):
    error = success = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        db_session = SessionUser()
        if db_session.query(User).filter_by(email=email).first():
            error = "Email exists."
        else:
            hashed = generate_password_hash(password)
            db_session.add(User(first_name=request.form.get("name"), email=email, password=hashed, role='customer'))
            db_session.commit()
            success = "Done."
        db_session.close()
    return render("pages/auth/register.html", request, title="Register", error=error, success=success)

def api_barcode_lookup(request):
    barcode = request.args.get("barcode", "").strip()
    db = SessionProd()
    product = db.query(Product).filter(Product.barcode == barcode).first()
    db.close()
    if product:
        return Response(json.dumps({"id": product.id}), status=200, content_type="application/json")
    return Response(json.dumps({"error": "Not found"}), status=404, content_type="application/json")

def contactus(request): return render("pages/info/contactus.html", request)
def thecompany(request): return render("pages/info/thecompany.html", request)
def thehistory(request): return render("pages/info/thehistory.html", request)
def services(request): return render("pages/info/services.html", request)
def orders(request):
    user_id = get_user_id(request)
    if not user_id: return redirect("/login")
    db_session = SessionProd()
    order_rows = db_session.query(Sale).filter_by(customer_id=user_id).order_by(Sale.id.desc()).all()
    results = []
    for o in order_rows:
        items = db_session.query(Sale_Item, Product).join(
            Product, Sale_Item.product_id == Product.id
        ).filter(Sale_Item.sale_id == o.id).all()
        order_items = []
        for sale_item, product in items:
            qty = int(sale_item.quantity or 0)
            unit_price = float(sale_item.unit_price or 0.0)
            subtotal = float(sale_item.line_total or (unit_price * qty))
            order_items.append({
                "product_name": (product.name if product else f"Product #{sale_item.product_id}"),
                "quantity": qty,
                "subtotal": subtotal
            })
        results.append({"order": o, "order_items": order_items})
    db_session.close()
    return render("pages/shop/orders.html", request, orders=results)

@Request.application
def app_logic(request):
    adapter = url_map.bind_to_environ(request.environ)
    try:
        endpoint, values = adapter.match()
        return globals()[endpoint](request, **values)
    except NotFound: return Response("404", status=404)
    except Exception as e: return Response(str(e), status=500)

app = SharedDataMiddleware(app_logic, {'/static': os.path.join(basedir, 'static')})

if __name__ == "__main__":
    run_simple("127.0.0.1", 5000, app, use_reloader=True)