import os
import bcrypt
import requests

from flask import Flask, session, render_template, request

from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

#from flask_bcrypt import Bcrypt
#bcrypt = Bcrypt(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    print("**********************************************************************************")
    if session.get('username'):
        return render_template("search.html")
    else:
        return render_template("index.html")

@app.route("/results", methods=["POST"])
def results():
    """ Return found books for the logged user """

    #Get form Information
    search_by = request.form.get("search_by")
    print(search_by)
    search_text = request.form.get("search_text")
    s = "SELECT * from books where lower(%s) like \'%%%s%%\'" % (search_by,search_text.lower())
    books = db.execute(s).fetchall()

    #Check the password

    # try:
    #     user_id = int(request.form.get("user_id"))
    # except ValueError:
    #     return render_template("error.html", message="Invalid flight number.")
    errorMsg = "%s not found!" % (search_by.capitalize())

    if books is None:
        return render_template("error.html", message=errorMsg)
    else:
        return render_template("results.html", books=books)

@app.route('/logout')
def logout():
   # remove the username from the session if it is there
   session.pop('username', None)
   session.pop('user_id', None)
   return render_template("index.html")

@app.route("/review/<int:book_id>", methods=["POST"])
def review(book_id):
    """ Create new review for user """

    #Get form Information
    review_text = request.form.get("review_text")
    review_rating = int(request.form.get("review_rating"))

    #s = "INSERT INTO reviews (rating, review, book_id, user_id) VALUES (%s, '%s', %s, %s)" % (review_rating, review_text, book_id, session['user_id'])

    db.execute("INSERT INTO reviews (rating, review, book_id, user_id) VALUES (:review_rating, :review_text, :book_id, :user_id)",
            {"review_rating": review_rating, "review_text": review_text, "book_id": book_id, "user_id": session['user_id']})
    db.commit()

    return render_template("success.html", message = "Your review has been submitted.", link="/")

@app.route("/search", methods=["POST"])
def search():
    """ Search for books with the logged user """

    #Get form Information
    username = request.form.get("username")
    passwd_to_check = request.form.get("password")

    hashed_passwd = db.execute("SELECT hashed_password from users where username =:username", {"username": username}).fetchone()
    user_id = db.execute("SELECT id from users where username =:username", {"username": username}).fetchone()
    user_id = user_id[0]

    #Check the password
    loginOK = bcrypt.checkpw(passwd_to_check.encode('utf-8'), hashed_passwd[0].encode('utf-8'))

    # try:
    #     user_id = int(request.form.get("user_id"))
    # except ValueError:
    #     return render_template("error.html", message="Invalid flight number.")

    if loginOK:
        session['username'] = username
        session['user_id'] = user_id
        return render_template("search.html")
    else:
        return render_template("error.html", message="Invalid login details.")

@app.route("/write_review/<int:book_id>")
def write_review(book_id):
    s = "SELECT * from books where id = %s" % (book_id)
    book = db.execute(s).fetchone()
    return render_template("write_review.html", book=book)

@app.route("/create_user")
def create_user():
    return render_template("create_user.html")

@app.route("/book_details/<int:book_id>")
def book_details(book_id):
    s = "SELECT * from books where id = %s" % (book_id)
    book = db.execute(s).fetchone()

    user_id = session['user_id']
    print(user_id)

    #s_review = "SELECT * from reviews where book_id = %s" % (book_id)
    #reviews = db.execute(s_review).fetchall()

    s_reviews = "SELECT username, name, rating, review FROM reviews r INNER JOIN users u ON r.user_id=u.id WHERE book_id=%s and  not user_id = %s" % (book_id, user_id)
    reviews = db.execute(s_reviews).fetchall()

    s_user_review = "select username, name, rating, review from reviews r INNER JOIN users u ON r.user_id = u.id WHERE book_id = %s and user_id = %s" % (book_id, user_id)
    user_review = db.execute(s_user_review).fetchone()

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "fhKxf4i1ZjcbxFBJQhD7bQ", "isbns": book.isbn})
    data = res.json()
    data = data['books']
    average_rating = data[0]['average_rating']
    number_of_ratings = data[0]['work_ratings_count']

    return render_template("book_details.html", book=book, average_rating=average_rating, number_of_ratings=number_of_ratings, reviews=reviews, user_review=user_review)


@app.route("/create_new_user", methods=["POST"])
def create_new_user():
    """ Create new user """

    #Get form Information
    username = request.form.get("username")
    password = request.form.get("password")
    name = request.form.get("name")
    email = request.form.get("email")

    hashed_passwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # try:
    #     user_id = int(request.form.get("user_id"))
    # except ValueError:
    #     return render_template("error.html", message="Invalid flight number.")

    db.execute("INSERT INTO users (username, hashed_password, name, email) VALUES (:username, :hashed_password, :name, :email)",
            {"username": username, "hashed_password": hashed_passwd, "name": name, "email": email})
    db.commit()

    return render_template("success.html", message="User created successfully!", link="/")
