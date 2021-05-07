import os
# Most of the initial configuration method is learnt from cs50 finance problem set
"""
SQL: store user info
flask: to render website
flask_session: using a login system
tempfile: storing session
werkzeug.security: adds function to store user's pass as hash
werkzeug.exceptions: if any exception happens, use a function: errorhandler(e), and app.errorhandler
datetime: store datetime when a message is sent
wraps: used in login_required function
"""
"""
https://flask-session.readthedocs.io/en/latest/ (session config documentation)
https://flask.palletsprojects.com/en/1.1.x/config/ (flask config documentation)
"""
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from datetime import datetime
from functools import wraps


"""Initiate app"""
app = Flask(__name__)

"""Auto-reload template files whenever there's a change, for better testing"""
app.config["TEMPLATES_AUTO_RELOAD"]

"""Config session as:
storing session in temp file
do not make it permanent
type=filesystem
"""
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""Access database"""
db = SQL("sqlite:///birthday-meet.db")
"""Database info:

CREATE TABLE users (
        id INTEGER,
        username TEXT NOT NULL,
        hash TEXT NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        PRIMARY KEY(id)
    );

CREATE UNIQUE INDEX username ON users (username);

CREATE TABLE requests (
        id INTEGER,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        request_message TEXT NOT NULL,
        when_sent DATE NOT NULL,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        PRIMARY KEY(id)
    );

CREATE TABLE friends (
        user_1_id INTEGER NOT NULL,
        user_2_id INTEGER NOT NULL,
        FOREIGN KEY (user_1_id) REFERENCES users (id),
        FOREIGN KEY (user_2_id) REFERENCES users (id)
    );

CREATE TABLE messages (
        id INTEGER,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        when_sent DATE NOT NULL,
        is_read BIT NOT NULL,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        PRIMARY KEY(id)
    );
"""

MONTHS = [None,"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

@app.after_request
def after_request(response):
    """Cache stores temp data on computer for faster load, but for our program, we don't want that
    This ensures that all cashe is cleared after each flask request
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def login_required(f):
    """This function detects if there is a "session" for user
    acts as a function decorator: @login_required
    If there's no session, redirect user to a login page
    If there is session, allow all function to do what they are supposed to do

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            # TODO: flash a message "You are not logged in"
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    """Home page

    If not logged in:
        Show introduction page to not signed in users
    If logged in:
        Show overview of account
            username
            birthday
            number of requests
            number of unread messages
            number of potential friends
    """
    if session.get("user_id") is None:
        # Scenario where user is not logged in
        return render_template("index.html")
    else:
        user_info = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))[0]
        user_id = user_info["id"]
        username = user_info["username"]
        birth_month = int(user_info["month"])
        birth_day = user_info["day"]
        birth_month_name = MONTHS[birth_month]

        # Count number of requests from db where receiver is user
        number_of_requests = len(db.execute("SELECT * FROM requests WHERE receiver_id = ?", user_id))

        # Count number of messages from db where receiver is user AND is_read is false
        number_of_unread_messages = len(db.execute("SELECT * FROM messages WHERE receiver_id = ? AND is_read = 0", user_id))

        # Potential friend is: id not user_id, month and day match, id not user_1 when user is user_2, id not user_2 when user is user_1, id not in requests where user's the sender
        number_of_potential_friends = len(db.execute("SELECT * FROM users WHERE id != ? AND month = ? AND day = ? AND id NOT IN (SELECT user_1_id FROM friends WHERE user_2_id = ?) AND id NOT IN (SELECT user_2_id FROM friends WHERE user_1_id = ?) AND id NOT IN (SELECT receiver_id FROM requests WHERE sender_id = ?)",
                                                     user_id, birth_month, birth_day, user_id, user_id, user_id))

        # Render the template with all necessary info to display in overview.html
        return render_template("overview.html",
                                username=username,
                                birth_month=birth_month,
                                birth_month_name = birth_month_name,
                                birth_day=birth_day,
                                number_of_requests=number_of_requests,
                                number_of_unread_messages=number_of_unread_messages,
                                number_of_potential_friends=number_of_potential_friends)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Clear all session info, log user in

    GET request displays a html form
    POST request verifies user login from database
        Error include:
            no username
            no password
            wrong username/pass
    include an error message dict that is all None by default,
        only give it value when error occured
        and pass it to html
        error messages are displayed AT where error occurs
    Only success login redirects to "/"
        GET requests/error POST renders same template
    """
    # Make sure no error message pops out by default, log out user automatically
    error = None
    session.clear()

    # Receiving from form in login.html
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Only proceed if both fields are filled out
        if (username and password):
            user_info_of_username = db.execute("SELECT * FROM users WHERE username = ?", username)

            # Only proceed if username exists AND password is correct.
            # Give session and redirect
            if len(user_info_of_username) == 1 and check_password_hash(user_info_of_username[0]["hash"], password):
                session["user_id"] = user_info_of_username[0]["id"]
                redirect("/")

        # If failed any of the requirements (filled in correct username and pass), generate error message and render template like a get request
        error = "Incorrect username or password"

    # Render login.html, and pass error message (if there is any)
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Log user out by clearing session"""
    session.clear()
    redirect("/")


@app.route("/register")
def register():
    """Clear all session info, register user

    GET request displays a html form
    POST request verifies user input, and log user in by giving user a session
        Errors include:
            no username
            username taken
            no password
            password don't match
            password too simple
    include an error message dict that is all None by default,
        only give it value when error occured
        and pass it to html
        error messages are displayed AT where error occurs
    Only success login redirects to "/", along with a flash message "You have successfully registered"
        GET requests/error POST renders same template
    """
    # TODO:


@app.route("/explore")
@login_required
def explore():
    """Display a page with all potential friends
        Same birthday
        Not in friendlist
        Not currently requesting by me
    Get request
        display all potential friends, with forms to "send request"
        and if wanted, send a request message (default is: "Hello, I'm {username}")
        if no potential friends, display a message
    Post:
        verify if the receiving user is ACTUALLY a potential friend
        If this user is currently requesting you, act as accepting the user request
            Flash: you are now friend with "username"
        add user to request list along with message (if it's empty, use the default message)
            Flash: request sent
        success post redirects back to /explore.
        error will render same page again (with error messages)
    Errors:
        invalid user (error if user is user himself)
        user already requested
        user already friend
    include an error message that is None by default,
        only give it value when error occured
        and pass it to html
        if there's error, display RED text on top of page
    flash will display GREEN text on top of page
    Only success redirects to "/explore"
        GET requests/error POST renders same template
    """
    # TODO


@app.route("/requests")
@login_required
def requests():
    """Display a page of all friend requests directed at user

    POST request is when user is accepting/ignoring requests
        verify if the request_id of the accepting/ignoring request exists in db
        verify that the request_id is directed at current user
            ANY ERROR lead to an error message "invalid request"
        remove request from db
            if choose to ignore: redirect back to same page
                and also flash "request ignored"
            if choose to accept:
                add requesting user_id to friend list
                flash "request accepted"
                redirect to same page
    GET request simply get all requests from db and display
    error:
        request doesn't exist
        request not directed at user
    Same thing with error messages,
        always render template with error, just that error is usually None
        if there's error, display at top of page.
    """
    # TODO


@app.route("/messages")
@login_required
def messages():
    """Display a page full of ALL messages (new ones first) (html file includes the message content, sender and message id)

    POST request is to set a message as 'read' from unread (you cant set read to unread)
        check if the message id you are trying to set as read is actually directed to you
        if not don't redirect, jump to end and render again
        if yes, mark as read, change to db, then simply redirect back to messages

    GET request displays all messages, including sender, send time, read/unread... if it's unread, include a button to set it as read.
    """
    # TODO

