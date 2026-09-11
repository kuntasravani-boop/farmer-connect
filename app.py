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

    # Get all orders
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


    # -------------------------------------------------
    # Smart Delivery Summary
    # -------------------------------------------------

    delivery_requests = connection.execute(
        """
        SELECT
            id,
            quantity,
            address,
            status
        FROM orders
        WHERE status = 'Delivery Requested'
        """
    ).fetchall()


    smart_delivery_count = len(delivery_requests)

    shared_delivery_count = 0

    new_vehicle_count = 0

    no_vehicle_count = 0


    # Check every delivery request
    for order in delivery_requests:

        vehicles = connection.execute(
            """
            SELECT
                id,
                capacity,
                destination,
                available
            FROM vehicles
            WHERE available = 1
               OR EXISTS (
                    SELECT 1
                    FROM orders
                    WHERE orders.vehicle_id = vehicles.id
                    AND orders.status IN (
                        'Vehicle Assigned',
                        'Driver Accepted',
                        'Out for Delivery'
                    )
               )
            """
        ).fetchall()


        shared_found = False

        new_vehicle_found = False


        order_address = (
            order["address"] or ""
        ).lower()


        for vehicle in vehicles:

            # Calculate current load
            load = connection.execute(
                """
                SELECT COALESCE(SUM(quantity), 0)
                    AS total_load
                FROM orders
                WHERE vehicle_id = ?
                AND status IN (
                    'Vehicle Assigned',
                    'Driver Accepted',
                    'Out for Delivery'
                )
                """,
                (vehicle["id"],)
            ).fetchone()


            current_load = load["total_load"]


            remaining_capacity = (
                vehicle["capacity"] - current_load
            )


            if remaining_capacity < order["quantity"]:
                continue


            vehicle_destination = (
                vehicle["destination"] or ""
            ).lower()


            # Check destination compatibility
            destination_match = (
                vehicle_destination in order_address
                or order_address in vehicle_destination
            )


            if destination_match:

                if current_load > 0:

                    shared_found = True

                else:

                    new_vehicle_found = True


        # Count recommendation type
        if shared_found:

            shared_delivery_count += 1

        elif new_vehicle_found:

            new_vehicle_count += 1

        else:

            no_vehicle_count += 1


    connection.close()


    return render_template(
        "dealer_dashboard.html",
        orders=orders,
        smart_delivery_count=smart_delivery_count,
        shared_delivery_count=shared_delivery_count,
        new_vehicle_count=new_vehicle_count,
        no_vehicle_count=no_vehicle_count
    )
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
@app.route("/smart-vehicle/<int:order_id>")
def smart_vehicle(order_id):

    connection = get_connection()

    # Get the new delivery order
    order = connection.execute(
        """
        SELECT
            orders.id,
            orders.quantity,
            orders.address,
            orders.status
        FROM orders
        WHERE orders.id = ?
        """,
        (order_id,)
    ).fetchone()

    if order is None:
        connection.close()
        return "<h1>Order not found.</h1>"


    # -------------------------------------------------
    # Get vehicles that are either:
    # 1. Available
    # OR
    # 2. Already carrying an active delivery
    # -------------------------------------------------

    vehicles = connection.execute(
        """
        SELECT
            vehicles.id,
            vehicles.vehicle_number,
            vehicles.vehicle_type,
            vehicles.capacity,
            vehicles.driver_name,
            vehicles.driver_phone,
            vehicles.current_location,
            vehicles.destination,
            vehicles.available
        FROM vehicles
        WHERE vehicles.available = 1
           OR EXISTS (
                SELECT 1
                FROM orders
                WHERE orders.vehicle_id = vehicles.id
                AND orders.status IN (
                    'Vehicle Assigned',
                    'Driver Accepted',
                    'Out for Delivery'
                )
           )
        """
    ).fetchall()


    recommendations = []


    # -------------------------------------------------
    # Prepare new order destination
    # -------------------------------------------------

    order_address = (order["address"] or "").lower()

    # Remove common punctuation
    order_address = (
        order_address
        .replace(",", " ")
        .replace("-", " ")
        .replace("/", " ")
    )

    order_locations = set(order_address.split())


    # Words that should NOT be treated as locations
    ignored_words = {
        "road",
        "street",
        "main",
        "near",
        "behind",
        "opposite",
        "beside",
        "village",
        "mandal",
        "district",
        "the"
    }

    order_locations = {
        word for word in order_locations
        if word not in ignored_words
    }


    # -------------------------------------------------
    # Check every vehicle
    # -------------------------------------------------

    for vehicle in vehicles:

        # Calculate current load of the vehicle
        load = connection.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) AS total_load
            FROM orders
            WHERE vehicle_id = ?
            AND status IN (
                'Vehicle Assigned',
                'Driver Accepted',
                'Out for Delivery'
            )
            """,
            (vehicle["id"],)
        ).fetchone()


        current_load = load["total_load"]

        remaining_capacity = (
            vehicle["capacity"] - current_load
        )


        # Vehicle destination
        vehicle_destination = (
            vehicle["destination"] or ""
        ).lower()

        vehicle_destination = (
            vehicle_destination
            .replace(",", " ")
            .replace("-", " ")
            .replace("/", " ")
        )

        vehicle_locations = set(
            vehicle_destination.split()
        )

        vehicle_locations = {
            word for word in vehicle_locations
            if word not in ignored_words
        }


        # -------------------------------------------------
        # Find common locations
        # -------------------------------------------------

        common_locations = (
            order_locations.intersection(
                vehicle_locations
            )
        )


        destination_match = len(common_locations) > 0


        # -------------------------------------------------
        # Check capacity
        # -------------------------------------------------

        enough_capacity = (
            remaining_capacity >= order["quantity"]
        )


        # -------------------------------------------------
        # Determine recommendation type
        # -------------------------------------------------

        shared_delivery = (
            destination_match
            and enough_capacity
            and current_load > 0
        )


        new_vehicle_recommendation = (
            destination_match
            and enough_capacity
            and current_load == 0
        )


        # Add vehicle if it has enough capacity
        if enough_capacity:

            recommendations.append({

                "vehicle": vehicle,

                "current_load": current_load,

                "remaining_capacity": remaining_capacity,

                "destination_match": destination_match,

                "shared_delivery": shared_delivery,

                "new_vehicle_recommendation":
                    new_vehicle_recommendation,

                "common_locations":
                    ", ".join(common_locations)

            })


    connection.close()


    # -------------------------------------------------
    # Sort recommendations
    #
    # 1. Shared delivery
    # 2. Destination match
    # 3. Remaining capacity
    # -------------------------------------------------

    recommendations.sort(
        key=lambda x: (
            x["shared_delivery"],
            x["destination_match"],
            x["remaining_capacity"]
        ),
        reverse=True
    )


    return render_template(
        "smart_vehicle.html",
        order=order,
        recommendations=recommendations
    )

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
@app.route("/assign-shared-vehicle/<int:order_id>/<int:vehicle_id>", methods=["POST"])
def assign_shared_vehicle(order_id, vehicle_id):

    connection = get_connection()

    # Get the new order
    order = connection.execute(
        """
        SELECT
            id,
            quantity,
            address,
            status
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    if order is None:
        connection.close()
        return "<h1>Order not found.</h1>"

    # Get the selected vehicle
    vehicle = connection.execute(
        """
        SELECT
            id,
            vehicle_number,
            capacity,
            destination
        FROM vehicles
        WHERE id = ?
        """,
        (vehicle_id,)
    ).fetchone()

    if vehicle is None:
        connection.close()
        return "<h1>Vehicle not found.</h1>"

    # Calculate current vehicle load
    load = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS total_load
        FROM orders
        WHERE vehicle_id = ?
        AND status IN (
            'Vehicle Assigned',
            'Driver Accepted',
            'Out for Delivery'
        )
        """,
        (vehicle_id,)
    ).fetchone()

    current_load = load["total_load"]

    remaining_capacity = (
        vehicle["capacity"] - current_load
    )

    # Check capacity
    if remaining_capacity < order["quantity"]:

        connection.close()

        return """
        <h1>Not enough vehicle capacity.</h1>
        <p>This vehicle cannot carry this order.</p>
        <a href="/smart-vehicle/{0}">Go Back</a>
        """.format(order_id)

    # Check destination
    order_address = (order["address"] or "").lower()
    vehicle_destination = (vehicle["destination"] or "").lower()

    if (
        vehicle_destination not in order_address
        and order_address not in vehicle_destination
    ):

        connection.close()

        return """
        <h1>Destination does not match.</h1>
        <p>This order cannot be added to this delivery.</p>
        <a href="/smart-vehicle/{0}">Go Back</a>
        """.format(order_id)

    # Assign order to existing vehicle
    connection.execute(
        """
        UPDATE orders
        SET vehicle_id = ?,
            status = 'Vehicle Assigned'
        WHERE id = ?
        """,
        (vehicle_id, order_id)
    )

    # Keep vehicle unavailable because it is carrying deliveries
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

    return """
    <h1>✅ Shared Delivery Assigned Successfully</h1>

    <p>Order FC{0} has been added to vehicle {1}.</p>

    <p>Status: Vehicle Assigned</p>

    <br>

    <a href="/delivery-management">
        Go to Delivery Management
    </a>
    """.format(
        order_id,
        vehicle["vehicle_number"]
    )

if __name__ == "__main__":
    app.run(debug=True)