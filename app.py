from flask import Flask, render_template, request

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

        # Temporary login for our first version
        if phone == "9876543210" and password == "farmer123":
            return """
            <h1>Welcome Farmer! 🌾</h1>
            <p>Login successful.</p>
            """

        return """
        <h1>❌ Invalid Login</h1>
        <a href="/login">Try Again</a>
        """

    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)