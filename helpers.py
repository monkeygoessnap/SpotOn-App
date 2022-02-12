import requests

from flask import redirect, render_template, session
from functools import wraps

# configurations
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
    

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# custom function for returning placename SG postalcode       
def placename(postal):
    params = {
           'searchVal': postal,
           'returnGeom': 'Y',
           'getAddrDetails': 'N',
           'pageNum': "1"
       }
    api_result = requests.get('https://developers.onemap.sg/commonapi/search', params, timeout=0.2)
    api_response = api_result.json()
    # print(api_response["results"][0]["SEARCHVAL"])
    return (api_response["results"][0]["SEARCHVAL"])

# custom function to create imagelocation for GET requests

def joinroute(file):
    r = ["/static/images/", file]
    route = "".join(r)
    return route

# custom function to create latlong values to plot into Folium from SG postalcode

def latlong(postal):    
    params = {
           'searchVal': postal,
           'returnGeom': 'Y',
           'getAddrDetails': 'N',
           'pageNum': "1"
       }
    api_result = requests.get('https://developers.onemap.sg/commonapi/search', params, timeout=0.2)
    api_response = api_result.json()
    coord = []
    coord.append(float(api_response["results"][0]["LATITUDE"]))
    coord.append(float(api_response["results"][0]["LONGITUDE"]))
    return coord
