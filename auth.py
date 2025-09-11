from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from db import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST

auth_bp = Blueprint("auth", __name__, template_folder="templates")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row[1], password):
            session['user'] = username
            session['user_id'] = row[0]
            return redirect(url_for("upload.index"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("login.html", error=error)

@auth_bp.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password)
        try:
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, pw_hash))
            conn.commit()
            flash("회원가입 완료! 로그인하세요.")
            return redirect(url_for("auth.login"))
        except mysql.connector.IntegrityError:
            error = "이미 존재하는 아이디입니다."
        finally:
            cursor.close()
            conn.close()
    return render_template("signup.html", error=error)

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("upload.index"))
