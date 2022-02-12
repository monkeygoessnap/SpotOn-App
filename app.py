import os
import folium
from folium import plugins

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from tempfile import TemporaryFile, mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, allowed_file, placename, joinroute, latlong

# Configure application
UPLOAD_FOLDER = './static/images'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response
    

# Custom Jinja filter
app.jinja_env.filters["joinroute"] = joinroute


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# Credits to Geonames.org for SG postal code data which was loaded into project.db by own custom function
db = SQL("sqlite:///project.db")

@app.route("/")
def index():
    """Home page"""
    return render_template("index.html")

@app.route("/me", methods=["GET"])
@login_required
def me():
    """Me Page"""
    sess_id = session["user_id"]
    rows = db.execute("SELECT * FROM spots WHERE p_id = ? ORDER BY date DESC, time DESC", sess_id)
    username = db.execute("SELECT username FROM users WHERE id = ?", sess_id)[0]["username"]
    try:
        r = rows[0]
    except Exception:
        r = 0
    return render_template("me.html", rows=rows, r=r, username=username)

@app.route("/profile", methods=["GET"])
@login_required
def profile():
    """Profile Page"""
    sess_id = session["user_id"]
    rows = db.execute("SELECT * FROM users WHERE id = ?", sess_id)
    return render_template("profile.html", rows=rows)
    

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """Change Profile Page"""
    sess_id = session["user_id"]
    
    if request.method == "POST":
        pw = generate_password_hash(request.form.get("password"))
        email = request.form.get("email")
        file = request.files["file"]
        sess_id = session["user_id"]
        
        # filename checker
        if allowed_file(file.filename):
            # own filenaming convention
            f = (str(sess_id), "_pp.", file.content_type[6:])
            filename = "".join(f)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            return apology("Invalid file", 400)
            
        # password confirmation
        if request.form.get("confirmation") != request.form.get("password"):
            return apology("password does not match", 400)
        
        # checks if there's a response
        if len(filename) > 1:
            db.execute("UPDATE users SET profilepic = ? WHERE id = ?", filename, sess_id)
        
        if len(request.form.get("password")) > 1:
            db.execute("UPDATE users SET hash = ? WHERE id = ?", pw, sess_id)
        
        if len(email) > 1:
            db.execute("UPDATE users SET email = ? WHERE id = ?", email, sess_id)
        
        return redirect("/profile")
        
    else:
        return render_template("change.html")
    
@app.route("/around", methods=["GET"])
@login_required
def around():
    """Around Me Page"""
    sess_id = session["user_id"]
    # Folium Map Initialization center to SG
    m = folium.Map(location=[1.3541, 103.8198], tiles="OpenStreetMap", zoom_start=12, control_scale=True)
    rows = db.execute(
        "SELECT des, date, time, pic, postal, lat, long, username, profilepic FROM spots JOIN users on users.id=spots.p_id WHERE id = ?", sess_id)
    
    custom_cluster = plugins.MarkerCluster(options={'showCoverageOnHover': False,
                                                    'zoomToBoundsOnClick': True,
                                                    'spiderfyOnMaxZoom': True,
                                                    'disableClusteringAtZoom': 14})
    
    for data in rows:
        # Checks if custom function returns a value for Lat Long
        if data["lat"] == None:
            continue
        else:
            try:
                pp = f"""<img src="{joinroute(data["profilepic"])}" style="height:30px;width:auto;margin-left:auto;border-radius:50%">"""
            except Exception:
                pp = ""
            # Custom HTML to render POPUP, credits to Pubs-of-Oxfordshire-Map. This section to render own user's
            custom = folium.Html(f"""<div id="box" style="width:200px"><img src="{joinroute(data["pic"])}" style="max-height:55%;max-width:100%" frameborder="0" scrolling="auto" allowtransparency="true">
            Event | {data["des"]}<br>
            By | {data["username"]} {pp}<br>
            On | {data["date"]}</div>
            """, script=True)
            popup = folium.Popup(custom, max_width=700)
            folium.Marker(
                location=[data["lat"], data["long"]],
                popup=popup,
                icon=folium.Icon(color="blue", icon="cloud")
            ).add_to(custom_cluster)
                
    rows = db.execute(
        "SELECT des, date, time, pic, postal, lat, long, username, profilepic FROM spots JOIN users on users.id=spots.p_id WHERE id != ?", sess_id)
    
    for data in rows:
        # Checks if custom function returns a value for Lat Long
        if data["lat"] == None:
            continue
        else:
            try: 
                pp = f"""<img src="{joinroute(data["profilepic"])}" style="height:30px;width:auto;margin-left:auto;border-radius:50%">"""
            except Exception:
                pp = ""
            # Custom HTML to render POPUP, credits to Pubs-of-Oxfordshire-Map. This section to render other user's
            custom = folium.Html(f"""<div id="box" style="width:200px"><img src="{joinroute(data["pic"])}" style="max-height:55%;max-width:100%" frameborder="0" scrolling="auto" allowtransparency="true">
            Event | {data["des"]}<br>
            By | {data["username"]} {pp}<br>
            On | {data["date"]}</div>
            """, script=True)
            popup = folium.Popup(custom, max_width=700)
            folium.Marker(
                location=[data["lat"], data["long"]],
                popup=popup,
                icon=folium.Icon(color="red", icon="cloud")
            ).add_to(custom_cluster)
                
    plugins.LocateControl(auto_start=False).add_to(m)
    custom_cluster.add_to(m)
    
    return render_template("around.html", map=m._repr_html_())


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create New"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        file = request.files["file"]
        sess_id = session["user_id"]
        
        # filename checker
        if allowed_file(file.filename):
            # filename = secure_filename(file.filename)
            filecount = db.execute("SELECT COUNT(p_id) FROM spots WHERE p_id = ?", sess_id)[0]["COUNT(p_id)"]
            f = (str(sess_id), str(filecount), "_img.", file.content_type[6:])
            # own filenaming convention
            filename = "".join(f)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            return apology("Invalid file", 400)
        
        des = request.form.get("des")
        postal = request.form.get("postal")
        
        _placename = ""
        try:
            _placename = placename(postal)
        except IndexError:
            return apology("Invalid postal", 400)

        coo = latlong(postal)
        _lat = coo[0]
        _long = coo[1]

        db.execute("INSERT INTO spots (p_id, des, pic, postal, placename, lat, long) VALUES (?, ?, ?, ?, ?, ?, ?)", sess_id, des, filename, postal, _placename, _lat, _long)
        
        # Redirect user to success
        return redirect("/me")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("create.html")
        

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/around")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        username = request.form.get("username")
        pw = generate_password_hash(request.form.get("password"))
        email = request.form.get("email")
    
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("password does not match", 400)
        
        elif len(rows) == 1:
            return apology("Username already exist", 400)
        
        db.execute("INSERT INTO users (username, hash, email) VALUES (?, ?, ?)", username, pw, email)
        
        # Redirect user to success
        return render_template("success.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)