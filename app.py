import csv
import os
from datetime import datetime
from io import StringIO
from flask import make_response, request
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import init_db, register_user, validate_user, validate_admin, add_event, get_user_events, get_all_events, delete_event
from config import SECRET_KEY
from database.db import save_login, get_login_history, get_event_by_id, update_event, search_user_events, search_all_events
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from database.db import update_admin_profile, get_admin_profile, update_user_profile, get_user_profile
from database.db import get_admin_theme, get_user_theme, get_all_users, delete_user, reset_user_password, update_user_password, get_user_by_id
from database.db import get_admin_password, update_admin_password

app = Flask(__name__)
app.secret_key = SECRET_KEY

init_db()

UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ========== USER ROUTES ==========

@app.route("/")
def home():
    return redirect(url_for("user_login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    theme="dark"
    if request.method == "POST":
        success = register_user(request.form["username"], request.form["password"], request.form["phone"] ,request.form["name"])
        if success:
            flash("Registered successfully. Please login.", "success")
            return redirect(url_for("user_login"))
        else:
            flash("Username already exists!", "error")
        print(request.form)
    return render_template("register.html",theme=theme)

@app.route("/login", methods=["GET", "POST"])
def user_login():
    theme="dark"
    if request.method == "POST":
        user_id = validate_user(request.form["username"], request.form["password"])
        if user_id:
            session["user_id"] = user_id
            session["username"] = request.form["username"]
            session["role"] = "user"
            save_login(user_id, "user")
            return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid credentials", "error")
    return render_template("login.html",theme=theme)

@app.route("/user/dashboard", methods=["GET", "POST"])
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("user_login"))

    if request.method == "POST" and "search" in request.form:
        keyword = request.form["search"]
        events = search_user_events(session["user_id"], keyword)
    elif request.method == "POST":
        add_event(session["user_id"], request.form["title"], request.form["person"],
                  request.form["date"], request.form["time"], request.form["note"])
        flash("Event added!", "success")
        return redirect(url_for("user_dashboard"))
    else:
        events = get_user_events(session["user_id"])
    theme = get_user_theme(session["user_id"]) 
    return render_template("user_dashboard.html", events=events, username=session["username"],theme=theme)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("user_login"))

@app.route("/delete/<int:event_id>")
def delete_my_event(event_id):
    if session.get("role") == "user":
        delete_event(event_id)
    return redirect(url_for("user_dashboard"))

@app.route("/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if session.get("role") != "user":
        return redirect(url_for("user_login"))

    event = get_event_by_id(event_id)
    if request.method == "POST":
        update_event(event_id, request.form["title"], request.form["person"],
                     request.form["date"], request.form["time"], request.form["note"])
        flash("Event updated!", "success")
        return redirect(url_for("user_dashboard"))
    theme = get_user_theme(session["user_id"])
    return render_template("edit_event.html", event=event, theme=theme)

@app.route("/user/settings", methods=["GET", "POST"])
def user_settings():
    if session.get("role") != "user":
        return redirect(url_for("user_login"))
    user_id = session["user_id"]
    profile = get_user_profile(user_id)
    if request.method == "POST":
        theme = request.form["theme"]
        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        update_user_profile(user_id, image_path, theme)

        flash("Profile updated!", "success")
        return redirect(url_for("user_settings"))
    theme = get_user_theme(session["user_id"])
    return render_template("user_settings.html", profile=profile, theme=theme)


@app.route("/user/reset_password", methods=["GET", "POST"])
def reset_password():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    user_id = session["user_id"]
    
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        user = get_user_by_id(user_id)
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("user_settings"))

        stored_hash = user[2]  # Assuming password is the 3rd column in the user row

        if check_password_hash(stored_hash, current_password):
            hashed_new = generate_password_hash(new_password)
            update_user_password(user_id, hashed_new)
            flash("Password updated successfully!", "success")
            return redirect(url_for("user_settings"))
        else:
            flash("Incorrect current password.", "danger")
    theme = get_user_theme(user_id)
    return render_template("reset_password.html", theme=theme)     
# ========== ADMIN ROUTES ==========

@app.route("/admin/edit/<int:event_id>/from_user/<int:user_id>", methods=["GET", "POST"])
def admin_edit_user_event(event_id, user_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    event = get_event_by_id(event_id)

    if request.method == "POST":
        update_event(
            event_id,
            request.form["title"],
            request.form["person"],
            request.form["date"],
            request.form["time"],
            request.form["note"]
        )
        flash("Event updated!", "success")
        if user_id:
            return redirect(url_for("admin_view_user_events", user_id=user_id))
        else:
            return redirect(url_for("admin_dashboard"))

    theme = get_admin_theme(session["admin_id"])
    return render_template("edit_event.html", event=event, theme=theme)

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_id = validate_admin(request.form["username"], request.form["password"])
        if admin_id:
            session["admin_id"] = admin_id
            session["role"] = "admin"
            session["admin_name"] = request.form["username"]
            save_login(admin_id, "admin")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin login", "error")
    theme = "dark"
    return render_template("admin_login.html",theme=theme)

@app.route("/admin/dashboard",methods=["GET", "POST"])
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))
    if request.method == "POST" and "search" in request.form:
        keyword = request.form["search"]
        events = search_all_events(keyword)
    else:
        events = get_all_events()
    theme = get_admin_theme(session["admin_id"])
    return render_template("admin_dashboard.html", events=events, admin=session.get("admin_name"),theme=theme)

@app.route("/admin/delete/<int:event_id>/from_user/<int:user_id>")
def admin_delete_user_event(event_id, user_id):
    if session.get("role") == "admin":
        delete_event(event_id)
    if user_id:
        return redirect(url_for("admin_view_user_events", user_id=user_id))
    else:
        return redirect(url_for("admin_dashboard"))

@app.route("/export")
def export_data():
    export_format = request.args.get("format", "csv").lower()  # default is csv

    if session.get("role") == "user":
        events = get_user_events(session["user_id"])
    elif session.get("role") == "admin":
        events = get_all_events()
    else:
        return redirect(url_for("login"))

    output = StringIO()
    if export_format == "txt":
            # Each field on its own line
        for e in events:
            user = e[6] if session.get("role") == "admin" else session["username"]
            output.write(f"ID    : {e[0]}\n")
            output.write(f"Title : {e[2]}\n")
            output.write(f"Person: {e[3]}\n")
            output.write(f"Date  : {e[4]}\n")
            output.write(f"Time  : {e[5]}\n")
            output.write(f"Note  : {e[6]}\n")
            output.write(f"User  : {user}\n")
            output.write("\n")  # Blank line between records

        filename = "events.txt"
        content_type = "text/plain"

    else:
        # Default to CSV format
        writer = csv.writer(output)
        writer.writerow(["ID", "Title", "Person", "Date", "Time", "Note", "User"])
        for e in events:
            user = e[6] if session.get("role") == "admin" else session["username"]
            writer.writerow([e[0], e[2], e[3], e[4], e[5], e[6], user])

        filename = "events.csv"
        content_type = "text/csv"

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = content_type
    return response

@app.route("/calendar")
def calendar_view():
    if session.get("role") not in ["user", "admin"]:
        return redirect(url_for("login"))
    if session["role"] == "user":
        events = get_all_events()
        events = get_user_events(session["user_id"])
    else:
        events = get_all_events()
    calendar_events = [
        {
            "title":e[2],
            "start": e[4]
        } 
        for e in events
    ]
    theme = get_admin_theme(session["admin_id"]) if session.get("role") == "admin" else get_user_theme(session["user_id"])
    return render_template("calendar.html", calendar_events=calendar_events, theme=theme)

@app.route("/admin/logins")
def view_logins():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))
    logs = get_login_history()
    theme = get_admin_theme(session["admin_id"])
    return render_template("login_logs.html", logs=logs, theme=theme)

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    admin_id = session["admin_id"]  # assuming same session key
    profile = get_admin_profile(admin_id)

    if request.method == "POST":

        theme = request.form["theme"]

        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        update_admin_profile(admin_id, image_path, theme)

        flash("Admin profile updated!", "success")
        return redirect(url_for("admin_settings"))
    theme = get_admin_theme(session["admin_id"])
    return render_template("admin_settings.html", profile=profile, theme=theme)

@app.route("/admin/users")
def admin_manage_users():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))
    
    users = get_all_users()
    theme = get_admin_theme(session["admin_id"])
    return render_template("admin_users.html", users=users, theme=theme)

@app.route("/admin/users/delete/<int:user_id>")
def admin_delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    delete_user(user_id)
    flash("User deleted.", "success")
    return redirect(url_for("admin_manage_users"))

@app.route("/admin/users/<int:user_id>/events")
def admin_view_user_events(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    events = get_user_events(user_id)
    theme = get_admin_theme(session["admin_id"])
    return render_template("admin_user_events.html", events=events, user_id=user_id, theme=theme)

@app.route("/admin/users/<int:user_id>/reset_password", methods=["GET", "POST"])
def admin_reset_user_password(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)
        reset_user_password(user_id, hashed_password)
        flash("Password has been reset!", "success")
        return redirect(url_for("admin_manage_users"))
    theme = get_admin_theme(session["admin_id"])
    return render_template("reset_user_password.html", user_id=user_id,theme=theme)

@app.route("/admin/reset_password", methods=["GET", "POST"])
def admin_reset_password():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    admin_id = session["admin_id"]

    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        stored_hash = get_admin_password(admin_id)

        if stored_hash:
            if check_password_hash(stored_hash, current_password):
                hashed_new = generate_password_hash(new_password)
                update_admin_password(admin_id, hashed_new)
                flash("Password updated successfully!", "success")
                return redirect(url_for("admin_reset_password"))
            else:
                flash("Incorrect current password.", "danger")
        else:
            flash("Admin not found.", "danger")

    theme = get_admin_theme(admin_id)
    return render_template("admin_reset_password.html", theme=theme)

if __name__ == "__main__":
    app.run(debug=True)

