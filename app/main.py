"""
FlashSale AWS - E-Commerce Backend
Domain: https://samdevops.online | Region: ap-south-1 (Mumbai)
Architecture: Route53 -> CloudFront -> WAF -> ALB -> EC2 AutoScaling -> ElastiCache + RDS Multi-AZ
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import boto3, pymysql, redis, json, os, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlashSale AWS",
    description="E-Commerce Flash Sale on AWS Mumbai (ap-south-1)",
    version="1.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Environment Variables (set from CloudFormation outputs)
AWS_REGION  = os.getenv("AWS_REGION",   "ap-south-1")
DB_HOST     = os.getenv("DB_HOST",      "localhost")
DB_NAME     = os.getenv("DB_NAME",      "flashsale")
DB_USER     = os.getenv("DB_USER",      "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD",  "changeme")
REDIS_HOST  = os.getenv("REDIS_HOST",   "localhost")
REDIS_PORT  = int(os.getenv("REDIS_PORT", "6379"))
SECRET_NAME = os.getenv("SECRET_NAME",  "flashsale/db-credentials")
PRODUCT_CACHE_TTL = 300   # 5 minutes
CART_CACHE_TTL    = 3600  # 1 hour


def get_db_credentials():
    """Fetch DB credentials from AWS Secrets Manager"""
    try:
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        secret = json.loads(client.get_secret_value(SecretId=SECRET_NAME)["SecretString"])
        return secret["username"], secret["password"]
    except Exception:
        return DB_USER, DB_PASSWORD


def get_db():
    """Get RDS MySQL connection"""
    u, p = get_db_credentials()
    return pymysql.connect(
        host=DB_HOST, user=u, password=p,
        database=DB_NAME, charset="utf8mb4", connect_timeout=5
    )


def get_redis():
    """Get ElastiCache Redis connection"""
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT,
        decode_responses=True, socket_connect_timeout=3
    )


def init_db():
    """Initialize database tables and seed 5 products on first startup"""
    try:
        conn = get_db()
        with conn.cursor() as c:
            # Create products table
            c.execute("""CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                stock INT DEFAULT 0,
                image_url VARCHAR(500),
                category VARCHAR(100),
                flash_sale_price DECIMAL(10,2),
                is_flash_sale BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

            # Create orders table
            c.execute("""CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""")

            # Seed 5 products only if table is empty
            c.execute("SELECT COUNT(*) FROM products")
            if c.fetchone()[0] == 0:
                c.executemany(
                    "INSERT INTO products(name,description,price,stock,image_url,category,flash_sale_price,is_flash_sale) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    [
                        ("iPhone 15 Pro",
                         "Apple flagship A17 Pro chip with titanium design - Flash Sale!",
                         89999, 999,
                         "https://fakestoreapi.com/img/81Zt42ioCgL._AC_SX679_.jpg",
                         "Electronics", 74999, True),

                        ('Samsung 55" 4K Smart TV',
                         "Crystal UHD 4K Smart TV with Alexa Built-in - Flash Sale!",
                         59999, 500,
                         "https://fakestoreapi.com/img/61mtL65D4cL._AC_SX679_.jpg",
                         "Electronics", 44999, True),

                        ("Nike Air Max 2024",
                         "Premium lightweight running shoes with Air cushioning - Flash Sale!",
                         12999, 2000,
                         "https://fakestoreapi.com/img/71pWzhdJNwL._AC_UL640_FMwebp_QL65_.jpg",
                         "Fashion", 9999, True),

                        ("MacBook Air M3",
                         "Apple Silicon M3 chip, 13-inch, 18-hour battery - Flash Sale!",
                         114900, 300,
                         "https://fakestoreapi.com/img/61IBBVJvSDL._AC_SY879_.jpg",
                         "Electronics", 99900, True),

                        ("Sony WH-1000XM5",
                         "Industry-leading noise cancelling wireless headphones - Flash Sale!",
                         29990, 1500,
                         "https://fakestoreapi.com/img/61U7T1koQqL._AC_SX679_.jpg",
                         "Electronics", 19990, True),
                    ]
                )
            conn.commit()
        conn.close()
        logger.info("✅ Database initialized with 5 products")
    except Exception as e:
        logger.error(f"DB init failed (running in demo mode): {e}")


@app.on_event("startup")
async def startup():
    init_db()


# ── Models ────────────────────────────────
class CartItem(BaseModel):
    product_id: int
    quantity: int

class OrderRequest(BaseModel):
    user_id: str
    product_id: int
    quantity: int


# ── Routes ────────────────────────────────

@app.get("/")
def root():
    """Serve the e-commerce frontend"""
    path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"app": "FlashSale AWS", "domain": "samdevops.online", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check endpoint for ALB - must return 200"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "region": "ap-south-1",
        "services": {}
    }
    try:
        get_redis().ping()
        status["services"]["elasticache"] = "✅ connected"
    except Exception as e:
        status["services"]["elasticache"] = f"⚠️ {e}"
    try:
        conn = get_db()
        conn.close()
        status["services"]["rds"] = "✅ connected"
    except Exception as e:
        status["services"]["rds"] = f"⚠️ {e}"
    return status


@app.get("/products")
def get_products(category: Optional[str] = None):
    """
    Get products - checks ElastiCache Redis first (Cache HIT),
    falls back to RDS MySQL (Cache MISS), then caches result in Redis.
    Demo mode if both unavailable.
    """
    key = f"products:{category or 'all'}"

    # Try Redis cache first
    try:
        r = get_redis()
        cached = r.get(key)
        if cached:
            return {"source": "⚡ ElastiCache Redis (Cache HIT)", "data": json.loads(cached)}
    except Exception:
        pass

    # Fetch from RDS MySQL
    try:
        conn = get_db()
        with conn.cursor() as c:
            if category:
                c.execute("SELECT * FROM products WHERE category=%s", (category,))
            else:
                c.execute("SELECT * FROM products")
            rows = c.fetchall()
            cols = [d[0] for d in c.description]
            prods = [dict(zip(cols, row)) for row in rows]
            for p in prods:
                for k, v in p.items():
                    if hasattr(v, "__float__"): p[k] = float(v)
                    elif hasattr(v, "isoformat"): p[k] = str(v)
        conn.close()
        # Cache in Redis for next request
        try:
            get_redis().setex(key, PRODUCT_CACHE_TTL, json.dumps(prods))
        except Exception:
            pass
        return {"source": "🗃️ RDS MySQL (Cache MISS - now cached)", "data": prods}
    except Exception:
        pass

    # Demo mode fallback
    return {"source": "📦 Demo Mode (DB not connected)", "data": [
        {"id": 1, "name": "iPhone 15 Pro", "price": 89999, "flash_sale_price": 74999,
         "is_flash_sale": True, "stock": 999, "category": "Electronics",
         "image_url": "https://fakestoreapi.com/img/81Zt42ioCgL._AC_SX679_.jpg",
         "description": "Apple flagship A17 Pro chip - Flash Sale!"},
        {"id": 2, "name": 'Samsung 55" 4K Smart TV', "price": 59999, "flash_sale_price": 44999,
         "is_flash_sale": True, "stock": 500, "category": "Electronics",
         "image_url": "https://fakestoreapi.com/img/61mtL65D4cL._AC_SX679_.jpg",
         "description": "Crystal UHD 4K Smart TV - Flash Sale!"},
        {"id": 3, "name": "Nike Air Max 2024", "price": 12999, "flash_sale_price": 9999,
         "is_flash_sale": True, "stock": 2000, "category": "Fashion",
         "image_url": "https://fakestoreapi.com/img/71pWzhdJNwL._AC_UL640_FMwebp_QL65_.jpg",
         "description": "Premium Running Shoes - Flash Sale!"},
        {"id": 4, "name": "MacBook Air M3", "price": 114900, "flash_sale_price": 99900,
         "is_flash_sale": True, "stock": 300, "category": "Electronics",
         "image_url": "https://fakestoreapi.com/img/61IBBVJvSDL._AC_SY879_.jpg",
         "description": "Apple Silicon M3 - Flash Sale!"},
        {"id": 5, "name": "Sony WH-1000XM5", "price": 29990, "flash_sale_price": 19990,
         "is_flash_sale": True, "stock": 1500, "category": "Electronics",
         "image_url": "https://fakestoreapi.com/img/61U7T1koQqL._AC_SX679_.jpg",
         "description": "Noise Cancelling Headphones - Flash Sale!"},
    ]}


@app.post("/cart/{user_id}/add")
def add_to_cart(user_id: str, item: CartItem):
    """Add item to cart - stored in ElastiCache Redis"""
    try:
        r = get_redis()
        k = f"cart:{user_id}"
        cart = json.loads(r.get(k) or "{}")
        pid = str(item.product_id)
        cart[pid] = cart.get(pid, 0) + item.quantity
        r.setex(k, CART_CACHE_TTL, json.dumps(cart))
        return {"message": "✅ Added to cart", "cart": cart, "storage": "⚡ ElastiCache Redis"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/cart/{user_id}")
def get_cart(user_id: str):
    """Get cart from ElastiCache Redis"""
    try:
        cart = json.loads(get_redis().get(f"cart:{user_id}") or "{}")
        return {"user_id": user_id, "cart": cart, "source": "⚡ ElastiCache Redis"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/orders")
def place_order(order: OrderRequest):
    """
    Place order with Redis distributed lock to prevent overselling.
    Updates stock in RDS MySQL and clears Redis cache.
    """
    lock = f"stock_lock:{order.product_id}"

    # Redis distributed lock - prevents overselling during flash sale
    try:
        r = get_redis()
        if not r.set(lock, "locked", nx=True, ex=5):
            raise HTTPException(429, "High demand! Please retry in a moment.")
    except redis.exceptions.RedisError:
        pass

    try:
        conn = get_db()
        with conn.cursor() as c:
            c.execute(
                "SELECT price, flash_sale_price, is_flash_sale, stock FROM products WHERE id=%s",
                (order.product_id,)
            )
            p = c.fetchone()
            if not p:
                raise HTTPException(404, "Product not found")

            price, fp, is_flash, stock = p
            if stock < order.quantity:
                raise HTTPException(400, f"Insufficient stock: only {stock} left!")

            unit = float(fp) if is_flash and fp else float(price)
            total = unit * order.quantity

            # Atomic stock update
            c.execute(
                "UPDATE products SET stock=stock-%s WHERE id=%s AND stock>=%s",
                (order.quantity, order.product_id, order.quantity)
            )
            c.execute(
                "INSERT INTO orders(user_id, product_id, quantity, total_price, status) VALUES(%s,%s,%s,%s,'confirmed')",
                (order.user_id, order.product_id, order.quantity, total)
            )
            oid = c.lastrowid
            conn.commit()
        conn.close()

        # Invalidate Redis cache so next request gets fresh stock
        try:
            get_redis().delete("products:all", f"products:{order.product_id}")
        except Exception:
            pass

        return {
            "order_id": oid,
            "total": total,
            "status": "confirmed",
            "message": f"🎉 Order confirmed! ₹{total:,.2f} saved to RDS MySQL"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            get_redis().delete(lock)
        except Exception:
            pass
