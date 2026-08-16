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
if __name__ == "__main__":
    app.run(debug=True)