from flask import Flask, render_template, request, redirect

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

    fertilizers = [
        {
            "name": "Urea",
            "price": 266,
            "stock": 100
        },
        {
            "name": "DAP",
            "price": 1350,
            "stock": 50
        },
        {
            "name": "NPK",
            "price": 1200,
            "stock": 80
        },
        {
            "name": "MOP",
            "price": 800,
            "stock": 40
        }
    ]

    return render_template(
        "products.html",
        fertilizers=fertilizers
    )


if __name__ == "__main__":
    app.run(debug=True)