from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("data.db")

@app.route("/")
def home():
    return "<h1>Hello!!! App is Running</h1><p>Use /add or /data</p>"

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
