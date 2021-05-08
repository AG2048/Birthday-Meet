# TODO:
# add flash to successful login/register/message sent/request sent/marked as read/accepted request/ignored request

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
from flask import Flask, flash, redirect, render_template, session, request
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
            flash("You are currently not logged in!")
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
    HTML:
        overview.html will be receiving:
        username
        birth_month,
        birth_month_name,
        birth_day,
        number_of_requests,
        number_of_unread_messages,
        number_of_potential_friends
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
    HTML:
        login.html will post:
            username
            password
        login.html can receive:
            error
    """
    # Make sure no error message pops out by default, log out user automatically
    error = None
    session.clear()

    # Receiving from form in login.html
    if request.method == "POST":
        username = request.form.get("username")

        # Only proceed if both fields are filled out
        if username and request.form.get("password"):
            user_info_of_username = db.execute("SELECT * FROM users WHERE username = ?", username)

            # Only proceed if username exists AND password is correct.
            # Give session and redirect
            if len(user_info_of_username) == 1 and check_password_hash(user_info_of_username[0]["hash"], request.form.get("password")):
                session["user_id"] = user_info_of_username[0]["id"]
                # TODO: add flash message
                flash("login success!")
                return redirect("/")
        # If failed any of the requirements (filled in correct username and pass), generate error message and render template like a get request
        error = "Incorrect username or password"

    # Render login.html, and pass error message (if there is any)
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Log user out by clearing session"""
    session.clear()
    # TODO: add flash message
    flash("Logout successful!")
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
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
    HTML:
        register.html will post:
            username
            password
            confirm
            month
            day
        can receive:
            username_error
            password_error
            confirm_error
            birthday_error
    """
    # Make sure no error message pops out by default, log out user automatically
    username_error = None
    password_error = None
    confirm_error = None
    birthday_error = None
    session.clear()

    # Receiving from form in register.html
    if request.method == "POST":
        username = request.form.get("username")

        # Proceed if username is entered
        if username:
            # Proceed if username does not exist in db
            if len(db.execute("SELECT * FROM users WHERE username = ?", username)) == 0:
                # Proceed if length of password is at least 8 characters
                if request.form.get("password") and len(request.form.get("password")) >= 8:
                    # Proceed if user entered same password twice
                    if request.form.get("password") == request.form.get("confirm"):
                        # At this point, username and password are all correct
                        month = request.form.get("month")
                        day = request.form.get("day")
                        # Proceed if both value are numeric
                        if month.isnumeric() and day.isnumeric() and 1 <= int(month) <= 12:
                            month = int(month)
                            day = int(day)
                            # Proceed if month and day match
                            if (month in [1, 3, 5, 7, 8, 10, 12] and 1 <= day <= 31) or (month in [4, 6, 9, 11] and 1 <= day <= 30) or (month == 2 and 1 <= day <= 29):
                                # Insert new user data into db
                                db.execute("INSERT INTO users (username, hash, month, day) VALUES (?, ?, ?, ?)", username, generate_password_hash(request.form.get("password")), month, day)
                                # Auto login user
                                session["user_id"] = db.execute("SELECT * FROM users WHERE username = ?", username)[0]["id"]
                                # TODO: add flash message
                                flash("Registration complete!")
                                return redirect("/")
                            else:
                                # Month and day doesn't match
                                birthday_error = "Invalid birthday"
                        else:
                            # Month or day is not numeric, and month is not one of 12 months
                            birthday_error = "Invalid birthday"
                    else:
                        # Passwords don't match
                        confirm_error = "Passwords do not match"
                else:
                    # Password is not entered, or it's too short
                    password_error = "Password need to be 8 characters long"
            else:
                # Username already exists
                username_error = "Username already taken"
        else:
            # Username not inputed
            username_error = "Invalid username"

    # Render login.html, and pass error message (if there is any)
    return render_template("register.html", username_error=username_error, password_error=password_error, confirm_error=confirm_error, birthday_error=birthday_error)


@app.route("/explore", methods=["GET", "POST"])
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
    HTML:
        explore.html will post:
            receiver_id
            request_message (can be blank)
        can receive:
            list_of_potential_friends (a dict of user's username AND id) (in html first check if it's empty) (can access data with dot notation or square bracket: dict.value or dict["value"])
                if list is empty display diff messages
            error
    """
    error = None

    if request.method == "POST":
        receiver_id = request.form.get("receiver_id")
        # Verify if receiver_id exixts AND is not user himself
        if receiver_id and receiver_id != session.get("user_id") and len(db.execute("SELECT * FROM users WHERE id = ?", receiver_id)) == 1:
            user_info = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))[0]
            receiver_info = db.execute("SELECT * FROM users WHERE id = ?", receiver_id)[0]

            user_birth_month = user_info["month"]
            user_birth_day = user_info["day"]
            receiver_birth_month = receiver_info["month"]
            receiver_birth_day = receiver_info["day"]
            # Verify if it is a "possible friend"
            if user_birth_month == receiver_birth_month and user_birth_day == receiver_birth_day:
                # Verify if the receiving user is not already a friend
                if len(db.execute("SELECT * FROM friends WHERE (user_1_id = ? AND user_2_id = ?) OR (user_1_id = ? AND user_2_id = ?)", session.get("user_id"), receiver_id, receiver_id, session.get("user_id"))) == 0:
                    # Verify if receiving user already being sent a friend request
                    if len(db.execute("SELECT * FROM requests WHERE sender_id = ? AND receiver_id = ?", session.get("user_id"), receiver_id)) == 0:
                        # if receiver has already sent to user a request
                        if len(db.execute("SELECT * FROM requests WHERE sender_id = ? AND receiver_id = ?", receiver_id, session.get("user_id"))) > 0:
                            # add this relationship to friend list, remove that request from list
                            db.execute("INSERT INTO friends (user_1_id, user_2_id) VALUES (?, ?)", session.get("user_id"), receiver_id)
                            db.execute("DELETE FROM requests WHERE sender_id = ? AND receiver_id = ?", receiver_id, session.get("user_id"))
                            # TODO: add flash message
                            flash("This user have already sent you a request, you are now friends!")
                            return redirect("/explore")
                        else:
                            # User are the first to send a request
                            # Get message and add a default if not specified
                            message = request.form.get("message")
                            if not message:
                                message = "Hello, I would like to add you as my friend!"
                            # Keep track of when is this request sent
                            now = datetime.now().strftime("%Y-%m-%d")
                            db.execute("INSERT INTO requests (sender_id, receiver_id, request_message, when_sent) VALUES (?, ?, ?, ?)", session.get("user_id"), receiver_id, message, now)
                            # TODO: add flash message
                            flash("Request sent successfully!")
                            return redirect("/explore")
                    else:
                        # User have already sent a request to receiver
                        error = "You have already sent a request"
                else:
                    # User and receiver are already linked in friends list
                    error = "User is already a friend"
            else:
                # User does not have same birthday as receiver
                error = "Invalid friend request"
        else:
            # receiver_id doesnt exist, receiver is user him/herself, or receiver doesn't exist in users list
            error = "Invalid friend request"

    list_of_potential_friends = []
    current_user_info = db.execute("SELECT * FROM users WHERE id = ?", session.get("user_id"))[0]
    month = current_user_info["month"]
    day = current_user_info["day"]
    # Get list of users where same birthday and not user himself/herself
    list_of_users_with_same_birthday = db.execute("SELECT * FROM users WHERE month = ? AND day = ? AND id != ?", month, day, session.get("user_id"))
    # Loop thru all users and find potential friend
    for user_with_same_birthday in list_of_users_with_same_birthday:
        if len(db.execute("SELECT * FROM requests WHERE sender_id = ? AND receiver_id = ?", session.get("user_id"), user_with_same_birthday.get("id"))) != 0:
            # User have already sent this person a request
            continue
        if len(db.execute("SELECT * FROM friends WHERE (user_1_id = ? AND user_2_id = ?) OR (user_1_id = ? AND user_2_id = ?)", session.get("user_id"), user_with_same_birthday.get("id"), user_with_same_birthday.get("id"), session.get("user_id"))) != 0:
            # User already friend with this person
            continue
        # This is a potential friend, add to list
        list_of_potential_friends.append({
            "username": user_with_same_birthday.get("username"),
            "id": user_with_same_birthday.get("id")
        })
    list_of_potential_friends.sort(key = lambda l: l["username"])
    return render_template("explore.html", error=error, list_of_potential_friends=list_of_potential_friends)


@app.route("/requests", methods=["GET", "POST"])
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
    HTML:
        get:
            error,
            list_of_all_requests (where receiver is user, include message, sender username, date sent, id of the request)
                if list is empty, display separate message
                For the list, all values' name is same as name in database
                sender_username
                request_message
                when_sent
        posts:
            request_id
            accept or not (accepts: true or false)
    """
    error = None
    if request.method == "POST":
        request_id = request.form.get("request_id")
        accepts = request.form.get("accepts")
        # Verify request_id and accepts are entered
        if request_id and accepts:
            request_info = db.execute("SELECT * FROM requests WHERE id = ?", request_id)
            # Check if this request_id actually refers to a request
            if len(request_info) == 1:
                request_info = request_info[0]
                # Make sure this request is for user
                if request_info["receiver_id"] == session.get("user_id"):
                    # Get sender's id, and remove the request from requests table
                    sender_id = request_info["sender_id"]
                    db.execute("DELETE FROM requests WHERE id = ?", request_id)
                    if accepts == "true":
                        # This request is accepted, add them into friend list
                        db.execute("INSERT INTO friends (user_1_id, user_2_id) VALUES (?, ?)", session.get("user_id"), sender_id)
                        # TODO: flash
                        flash("Request accepted!")
                        return redirect("/requests")
                    elif accepts == "false":
                        # user is ignoring this request, don't do anything. Just redirect
                        flash("Request ignored!")
                        return redirect("/requests")
                    else:
                        # Error here, accepts is not true nor false
                        error = "Invalid action"
                else:
                    # this request is not directed at user
                    error = "Invalid friend request"
            else:
                # request doesn't exist in requests table
                error = "Invalid friend request"
        else:
            # There are no request_id passed on, or "accepts" is not passed. MISSING INFORMATION
            error = "Invalid input"
    # Get data of all requests directed to this person from database, then render
    list_of_all_requests = db.execute("SELECT * FROM requests WHERE receiver_id = ?", session.get("user_id"))
    for every_request in list_of_all_requests:
        every_request["sender_username"] = db.execute("SELECT * FROM users WHERE id = ?", every_request["sender_id"])[0]["username"]
    list_of_all_requests.reverse()
    return render_template("requests.html", error=error, list_of_all_requests=list_of_all_requests)


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    """Display a page full of ALL messages (new ones first) (html file includes the message content, sender and message id)

    POST request is to set a message as 'read' from unread (you cant set read to unread)
        check if the message id you are trying to set as read is actually directed to you
        if not don't redirect, jump to end and render again
        if yes, mark as read, change to db, then simply redirect back to messages

    GET request displays all messages, including sender, send time, read/unread... if it's unread, include a button to set it as read.
    HTML:
        get: pass on a list of messages (each is a dict with message, id of message (for post requests), sender username, sent time, is_read (true or false))
            (list_of_messages_info =>message, id, sender_username, time_sent, is_read)
        post: app.py receives the id of the message to "mark as read" (message_id)
    """
    error = None

    if request.method == "POST":
        id_of_message_to_mark = request.form.get("message_id")
        if id_of_message_to_mark and id_of_message_to_mark.isnumeric():
            # Get message's info from db, where id is what I want AND it's directed at user
            message = db.execute("SELECT * FROM messages WHERE id = ? AND receiver_id = ?", id_of_message_to_mark, session.get("user_id"))
            if len(message) == 1:
                if message[0]["is_read"] == 0:
                    # Update message as read
                    db.execute("UPDATE messages SET is_read = 1 WHERE id = ? AND receiver_id = ?", id_of_message_to_mark, session.get("user_id"))
                    # TODO: flash
                    flash("Message marked as read!")
                    return redirect("/messages")
                else:
                    # message is already read...
                    error = "Message is already marked as read"
            else:
                # message doesn't exist, or message is not directed at current user (both will cause len() 0 from SELECT)
                error = "Invalid message"
        else:
            # Id isn't returned or id is not a number
            error = "Invalid input"
    # Init a list to return later
    list_of_messages_info = []
    # Get necessary info
    list_of_messages_from_database = db.execute("SELECT * FROM messages WHERE receiver_id = ?", session.get("user_id"))
    for message_from_database in list_of_messages_from_database:
        # From db get username of sender
        sender_username = db.execute("SELECT * FROM users WHERE id = ?", message_from_database["sender_id"])[0]["username"]
        # This turns the BIT into True/False
        is_read = (message_from_database["is_read"] == 1)
        list_of_messages_info.append({
            "message": message_from_database["message_text"],
            "id": message_from_database["id"],
            "sender_username": sender_username,
            "time_sent": message_from_database["when_sent"],
            "is_read": is_read
        })
    # Reverse so newest comes first
    list_of_messages_info.reverse()
    return render_template("messages.html", list_of_messages_info=list_of_messages_info, error=error)


@app.route("/friends")
@login_required
def friends():
    friends_usernames = []
    friend_id_lists_a = db.execute("SELECT user_2_id FROM friends WHERE user_1_id = ?", session.get("user_id"))
    friend_id_lists_b = db.execute("SELECT user_1_id FROM friends WHERE user_2_id = ?", session.get("user_id"))
    for friend_id in friend_id_lists_a:
        friends_usernames.append(db.execute("SELECT username FROM users WHERE id = ?", friend_id)[0]["username"])
    for friend_id in friend_id_lists_b:
        friends_usernames.append(db.execute("SELECT username FROM users WHERE id = ?", friend_id)[0]["username"])
    friends_usernames.sort()
    return render_template("friends.html", friends_usernames=friends_usernames)

# TODO
# add /friends (there should be a page just to see all your friends)
# add /send
# add /sent
# add a /contact, where people can send messages to the moderators, submiting a form.
# if have time, add a character limit to request messages?

