# Birthday-Meet
#### Video Demo:
#### Description:
Have you ever had the thought of meeting someone who shares your birthday, but it just seems impossible to meet anyone like that?

Well, Birthday Meet is the solution to that problem! With this online social platform, you can easily find other people who share your birthday and send message to them to make new friends!

##### Home Page:
`href="/"` `index.html`

In the home page, the user will be seeing a brief description of this website and the logo, along with two buttons to [Register](#Register) and [Log in](#Log-In).

All pages other than [Home Page](#Home-Page), [Register](#Register), and [Log in](#Log-In) require user to be logged in.

##### Register:
`href="/register"` `register.html`

This page allows user to register a new account with username, password, and a birthday. This page will redirect user to [Overview](#Overview) after registration.

##### Log In:
`href="/login"` `login.html`

This page allows user to log in to an existing account with username and password. This page will redirect user to [Overview](#Overview) after log in.

##### Overview:
`href="/"` after log in `overview.html`

This page displays user's basic information (username and birthday), along with some status information (number of unresponded friend requests, number of unread messages, number of potential friends to be added)

##### Explore:
`href="/explore"` after log in `explore.html`

This page displays all the potential friends to be added (other users with the same birthday as user that are not user's friend, and user have not yet sent a friend request), and allows user to send friend requests to them (with optional request message). 

There is a default request message if the user did not enter a request message.

If there are no potential friends, it will display a different message.

##### Requests:
`ref="/requests"` after log in `requests.html`

This page displays all unresponded friend requests that is directed to the user. The user may accept (which adds the sender to user's friend list) or ignore (the request is deleted, and the sender may send another request)

If there are no requests, it will display a different message.

##### Friends:
`ref="/friends"` after log in `friends.html`

This page displays a list of the user's friends' usernames.

If the user have no friends, it will display a different message.

##### Messages:
`ref="/messages"` after log in `messages.html`

This page displays a list of all messages directed to user, and allows user to mark an `unread` message `read`

This page also includes two buttons to direct users to [Send](#Send) and [Sent](#Sent).

If the user has not received any message, it will display a different message.

##### Send:
`ref="/send"` after log in `send.html`

This page allows user to select one of user's friends to send a message. 

If the user has not sent any message, it will display a different message.

##### Sent:
`ref="/sent"` after log in `sent.html`

This page displays a list of all messages sent by user, displays if the message is `read` or `unread`.

This page also includes two buttons to direct users to [Send](#Send) and [Messages](#Messages).

##### Contact Us:
`ref="/contact"` after log in `contact.html`

This page allows user to send a message to the developers of the website, which can only be read by accessing the database file.
