from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("data.db")

@app.route("/")
def home():
    return """
    <html>
        <head>
            <title>Flask App</title>
            <style>
                body {
                    background: linear-gradient(to right, #1e3c72, #2a5298);
                    color: white;
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                h1 {
                    font-size: 50px;
                }
                p {
                    font-size: 20px;
                }
                .box {
                    background-color: rgba(0, 0, 0, 0.4);
                    padding: 20px;
                    border-radius: 10px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>Hello!!! App is Running</h1>
                <p>Use /add or /data</p>
            </div>
        </body>
    </html>
    """

@app.route("/health")
def health():
    return jsonify(status="ok")

@app.route("/add")
def add():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS items (name TEXT)")
    db.execute("INSERT INTO items VALUES ('hello')")
    db.commit()
    return "Inserted"

@app.route("/data")
def data():
    db = get_db()
    rows = db.execute("SELECT name FROM items").fetchall()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7003)