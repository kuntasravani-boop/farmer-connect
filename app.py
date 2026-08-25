from flask import Flask, render_template, request, redirect
from database import get_connection

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>🌾 Farmer Connect</h1>
    <h2>Welcome to Farmer Connect</h2>
    <p>Connecting farmers, dealers and delivery partners.</p>

    <a href="/login">
        <button>Farmer Login</button>
    </a>
    """


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        phone = request.form["phone"]
        password = request.form["password"]

        if phone == "9876543210" and password == "farmer123":
            return render_template("farmer_dashboard.html")

        return """
        <h1>❌ Invalid Login</h1>
        <a href="/login">Try Again</a>
        """

    return render_template("login.html")


@app.route("/logout")
def logout():
    return redirect("/")

@app.route("/products")
def products():

    connection = get_connection()

    fertilizers = connection.execute("""
        SELECT id, name, price, stock
        FROM fertilizers
    """).fetchall()

    connection.close()

    return render_template(
        "products.html",
        fertilizers=fertilizers
    )
@app.route("/buy/<int:fertilizer_id>", methods=["GET", "POST"])
def buy_fertilizer(fertilizer_id):

    connection = get_connection()

    fertilizer = connection.execute(
        """
        SELECT id, name, price, stock
        FROM fertilizers
        WHERE id = ?
        """,
        (fertilizer_id,)
    ).fetchone()

    connection.close()

    if fertilizer is None:
        return "<h1>Fertilizer not found</h1>"

    if request.method == "POST":

        quantity = int(request.form["quantity"])
        address = request.form["address"]

        if quantity <= 0:
            return "<h1>Quantity must be greater than 0.</h1>"

        if quantity > fertilizer["stock"]:
            return "<h1>Not enough fertilizer available.</h1>"

        connection = get_connection()

        farmer = connection.execute(
            "SELECT id FROM farmers WHERE phone = ?",
            ("9876543210",)
        ).fetchone()

        if farmer is None:
            connection.close()
            return "<h1>Farmer account not found.</h1>"

        connection.execute(
            """
            INSERT INTO orders
            (farmer_id, fertilizer_id, quantity, delivery_type, address, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                farmer["id"],
                fertilizer["id"],
                quantity,
                "Pending",
                address,
                "Pending Dealer Confirmation"
            )
        )

        connection.commit()

        order_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        connection.close()

        return render_template(
            "order_success.html",
            order_id=order_id,
            fertilizer=fertilizer,
            quantity=quantity
        )

    return render_template(
        "order_form.html",
        fertilizer=fertilizer
    )
@app.route("/dealer-login", methods=["GET", "POST"])
def dealer_login():

    if request.method == "POST":

        phone = request.form["phone"]
        password = request.form["password"]

        connection = get_connection()

        dealer = connection.execute(
            """
            SELECT id, name
            FROM dealers
            WHERE phone = ? AND password = ?
            """,
            (phone, password)
        ).fetchone()

        connection.close()

        if dealer:

            return redirect("/dealer-dashboard")

        return """
        <h1>❌ Invalid Dealer Login</h1>
        <a href="/dealer-login">Try Again</a>
        """

    return render_template("dealer_login.html")
@app.route("/dealer-dashboard")
def dealer_dashboard():

    connection = get_connection()

    orders = connection.execute(
        """
        SELECT
            orders.id,
            farmers.name AS farmer_name,
            farmers.phone AS farmer_phone,
            fertilizers.name AS fertilizer_name,
            orders.quantity,
            orders.address,
            orders.status
        FROM orders
        JOIN farmers
            ON orders.farmer_id = farmers.id
        JOIN fertilizers
            ON orders.fertilizer_id = fertilizers.id
        ORDER BY orders.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "dealer_dashboard.html",
        orders=orders
    )

    return redirect("/dealer-dashboard")
    connection.commit()
    connection.close()

    return redirect("/dealer-dashboard")

@app.route("/dealer/confirm/<int:order_id>")
def confirm_order(order_id):

    connection = get_connection()

    connection.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            "Dealer Confirmed - Awaiting Pickup/Delivery Choice",
            order_id
        )
    )
    connection.commit()
    connection.close()

    return redirect("/dealer-dashboard")
@app.route("/dealer/reject/<int:order_id>")
def reject_order(order_id):

    connection = get_connection()

    connection.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            "Rejected by Dealer",
            order_id
        )
    )
    connection.commit()
    connection.close()

    return redirect("/dealer-dashboard")
@app.route("/my-orders")
def my_orders():

    connection = get_connection()

    farmer = connection.execute(
        """
        SELECT id
        FROM farmers
        WHERE phone = ?
        """,
        ("9876543210",)
    ).fetchone()

    if farmer is None:
        connection.close()
        return "<h1>Farmer account not found.</h1>"

    orders = connection.execute(
    """
    SELECT
        orders.id,
        fertilizers.name AS fertilizer_name,
        fertilizers.price,
        orders.quantity,
        orders.address,
        orders.status,
        orders.delivery_type,
        vehicles.vehicle_number,
        vehicles.vehicle_type,
        vehicles.driver_name,
        vehicles.driver_phone
    FROM orders
    JOIN fertilizers
        ON orders.fertilizer_id = fertilizers.id
    LEFT JOIN vehicles
        ON orders.vehicle_id = vehicles.id
    WHERE orders.farmer_id = ?
    ORDER BY orders.id DESC
    """,
    (farmer["id"],)
).fetchall()

    connection.close()

    return render_template(
        "my_orders.html",
        orders=orders
    )

@app.route("/order/<int:order_id>/delivery-choice", methods=["POST"])
def delivery_choice(order_id):

    delivery_type = request.form["delivery_type"]

    if delivery_type not in ["Self Pickup", "Home Delivery"]:
        return "<h1>Invalid delivery choice.</h1>"

    connection = get_connection()

    order = connection.execute(
        """
        SELECT id, status
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    if order is None:
        connection.close()
        return "<h1>Order not found.</h1>"

    if order["status"] != "Dealer Confirmed - Awaiting Pickup/Delivery Choice":
        connection.close()
        return "<h1>Delivery choice is not available for this order.</h1>"

    if delivery_type == "Self Pickup":
        status = "Ready for Pickup"
    else:
        status = "Delivery Requested"

    connection.execute(
        """
        UPDATE orders
        SET delivery_type = ?, status = ?
        WHERE id = ?
        """,
        (
            delivery_type,
            status,
            order_id
        )
    )

    connection.commit()
    connection.close()

    return redirect("/my-orders")

@app.route("/delivery-management")
def delivery_management():

    connection = get_connection()

    orders = connection.execute(
        """
        SELECT
            orders.id,
            farmers.name AS farmer_name,
            farmers.phone AS farmer_phone,
            fertilizers.name AS fertilizer_name,
            orders.quantity,
            orders.address,
            orders.status,
            orders.vehicle_id,
            vehicles.vehicle_number,
            vehicles.vehicle_type,
            vehicles.driver_name,
            vehicles.driver_phone
        FROM orders
        JOIN farmers
            ON orders.farmer_id = farmers.id
        JOIN fertilizers
            ON orders.fertilizer_id = fertilizers.id
        LEFT JOIN vehicles
            ON orders.vehicle_id = vehicles.id
        WHERE orders.status IN (?, ?, ?, ?)
        ORDER BY orders.id DESC
        """,
        (
            "Delivery Requested",
            "Vehicle Assigned",
            "Driver Accepted",
            "Out for Delivery"
        )
    ).fetchall()

    vehicles = connection.execute(
        """
        SELECT
            id,
            vehicle_number,
            vehicle_type,
            capacity,
            driver_name,
            driver_phone,
            current_location,
            destination
        FROM vehicles
        WHERE available = 1
        ORDER BY capacity ASC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "delivery_management.html",
        orders=orders,
        vehicles=vehicles
    )
@app.route("/update-delivery-status/<int:order_id>/<status>", methods=["POST"])
def update_delivery_status(order_id, status):

    allowed_statuses = [
        "Driver Accepted",
        "Out for Delivery",
        "Delivered"
    ]

    if status not in allowed_statuses:
        return "Invalid delivery status", 400

    connection = get_connection()

    order = connection.execute(
        """
        SELECT id, vehicle_id, status
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    if order is None:
        connection.close()
        return "Order not found", 404

    connection.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (status, order_id)
    )

    # When delivery is completed,
    # make the vehicle available again.
    if status == "Delivered" and order["vehicle_id"]:

        connection.execute(
            """
            UPDATE vehicles
            SET available = 1
            WHERE id = ?
            """,
            (order["vehicle_id"],)
        )

    connection.commit()
    connection.close()

    return redirect("/delivery-management")
@app.route("/assign-vehicle/<int:order_id>/<int:vehicle_id>", methods=["POST"])
def assign_vehicle(order_id, vehicle_id):

    connection = get_connection()

    # Check the order
    order = connection.execute(
        """
        SELECT id, quantity, status
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    if order is None:
        connection.close()
        return "<h1>Order not found.</h1>"

    # Check the vehicle
    vehicle = connection.execute(
        """
        SELECT id, vehicle_number, capacity, available
        FROM vehicles
        WHERE id = ?
        """,
        (vehicle_id,)
    ).fetchone()

    if vehicle is None:
        connection.close()
        return "<h1>Vehicle not found.</h1>"

    # Check vehicle availability
    if vehicle["available"] != 1:
        connection.close()
        return "<h1>This vehicle is currently unavailable.</h1>"

    # Check capacity
    if vehicle["capacity"] < order["quantity"]:
        connection.close()
        return "<h1>Vehicle capacity is insufficient for this order.</h1>"

    # Assign vehicle to order
    connection.execute(
        """
        UPDATE orders
        SET vehicle_id = ?,
            status = ?
        WHERE id = ?
        """,
        (
            vehicle_id,
            "Vehicle Assigned",
            order_id
        )
    )

    # Make vehicle unavailable
    connection.execute(
        """
        UPDATE vehicles
        SET available = 0
        WHERE id = ?
        """,
        (vehicle_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/delivery-management")

if __name__ == "__main__":
    app.run(debug=True)