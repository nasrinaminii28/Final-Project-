from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "ase moon-secret-key"

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR PASSWORD",
        database="db_class"
    )

@app.route("/")
def home():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM images")
    image_count = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM articles")
    article_count = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    user_count = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT *
        FROM images
        ORDER BY id DESC
        LIMIT 3
    """)
    latest_images = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM articles
        ORDER BY id DESC
        LIMIT 3
    """)
    latest_articles = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "home.html",
        image_count=image_count,
        article_count=article_count,
        user_count=user_count,
        latest_images=latest_images,
        latest_articles=latest_articles
    )

@app.route("/admin")
def admin():

    if "user_code" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied"

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM users
    """)
    users = cursor.fetchall()

    cursor.execute("""
        SELECT
            images.*,
            users.name AS photographer_name
        FROM images
        LEFT JOIN users
        ON images.photographer_code = users.code
        ORDER BY images.id 
    """)
    images = cursor.fetchall()

    cursor.execute("""
        SELECT
            articles.*,
            users.name AS writer_name
        FROM articles
        LEFT JOIN users
        ON articles.writer_code = users.code
        ORDER BY articles.id
    """)
    articles = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin.html",
        users=users,
        images=images,
        articles=articles
    )
    
@app.route("/admin/edit-user/<code>", methods=["GET", "POST"])
def edit_user(code):
    
    if "user_code" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied"

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM users
        WHERE code = %s
    """, (code,))

    user = cursor.fetchone()

    if user is None:
        cursor.close()
        db.close()
        return "User not found"

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        work_field = request.form["work_field"]
        role = request.form["role"]

        cursor.execute("""
            UPDATE users
            SET
                name = %s,
                email = %s,
                work_field = %s,
                role = %s
            WHERE code = %s
        """, (
            name,
            email,
            work_field,
            role,
            code
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(url_for("admin"))

    cursor.close()
    db.close()

    return render_template(
        "edit_user.html",
        user=user
    )

@app.route("/delete-user/<code>", methods=["POST"])
def delete_user(code):

    if "user_code" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied"

    if code == session["user_code"]:
        return "You cannot delete your own account"

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT image_path
        FROM images
        WHERE photographer_code = %s
    """, (code,))

    images = cursor.fetchall()

    images_folder = os.path.join(
        app.root_path,
        "static",
        "images"
    )

    for image in images:

        filename = os.path.basename(
            image["image_path"]
        )

        image_file_path = os.path.join(
            images_folder,
            filename
        )

        if os.path.exists(image_file_path):
            os.remove(image_file_path)

    cursor.execute("""
        DELETE FROM images
        WHERE photographer_code = %s
    """, (code,))

    cursor.execute("""
        DELETE FROM articles
        WHERE writer_code = %s
    """, (code,))

    cursor.execute("""
        DELETE FROM users
        WHERE code = %s
    """, (code,))

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        url_for("admin")
    )

def generate_user_code():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT code
        FROM users
        WHERE code LIKE 'U%'
        ORDER BY code DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    cursor.close()
    db.close()

    if result is None:
        return "U001"

    last_code = result[0]

    number = int(last_code[1:])

    new_number = number + 1

    return f"U{new_number:03d}"

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        work_field = request.form["work_field"]

        code = generate_user_code()

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO users
            (code, name, email, password, role, work_field)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            code,
            name,
            email,
            hashed_password,
            "user",
            work_field
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db()

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_code"] = user["code"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        return "Invalid email or password"

    return render_template("login.html")

@app.route("/images")
def images():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    category = request.args.get("category")
    search = request.args.get("search")

    query = """
        SELECT
            images.*,
            users.name AS photographer_name
        FROM images
        LEFT JOIN users
        ON images.photographer_code = users.code
        WHERE 1=1
    """

    values = []

    if category and category != "All":
        query += " AND images.category=%s"
        values.append(category)

    if search:
        query += """
            AND (
                images.title LIKE %s
                OR images.tags LIKE %s
                OR images.description LIKE %s
            )
        """

        keyword = "%" + search + "%"

        values.extend([keyword, keyword, keyword])

    cursor.execute(query, values)

    images = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM images")
    categories = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "images.html",
        images=images,
        categories=categories,
        selected=category,
        search=search
    )
     
@app.route('/image/<path:image_path>')
def image_details(image_path):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        images.*,
        users.name AS photographer_name,
        users.email AS photographer_email
    FROM images
    LEFT JOIN users
    ON images.photographer_code = users.code
    WHERE images.image_path=%s
    """, (image_path,))

    image = cursor.fetchone()


    cursor.close()
    db.close()

    return render_template(
        "image_details.html",
        image=image
    )

@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():

    # کاربر باید وارد حسابش شده باشد
    if "user_code" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        file = request.files.get("image")

        if not file or file.filename == "":
            return "Please select an image"

        title = request.form["title"]
        tags = request.form["tags"]
        description = request.form["description"]
        category = request.form["category"]

        filename = file.filename

        images_folder = os.path.join(
            app.root_path,
            "static",
            "images"
        )

        os.makedirs(
            images_folder,
            exist_ok=True
        )

        file_path = os.path.join(
            images_folder,
            filename
        )

        file.save(file_path)

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO images
            (
                image_path,
                title,
                tags,
                description,
                category,
                photographer_code
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            filename,
            title,
            tags,
            description,
            category,
            session["user_code"]
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "person",
                code=session["user_code"]
            )
        )

    return render_template("upload_image.html")

@app.route("/edit-image/<int:id>", methods=["GET", "POST"])
def edit_image(id):

    if "user_code" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if session.get("role") == "admin":

        cursor.execute("""
            SELECT *
            FROM images
            WHERE id = %s
        """, (id,))

    else:

        cursor.execute("""
            SELECT *
            FROM images
            WHERE id = %s
            AND photographer_code = %s
        """, (
            id,
            session["user_code"]
        ))

    image = cursor.fetchone()

    if image is None:
        cursor.close()
        db.close()

        return "Image not found or access denied"

    if request.method == "POST":

        title = request.form["title"]
        tags = request.form["tags"]
        description = request.form["description"]
        category = request.form["category"]

        file = request.files.get("image")

        if file and file.filename != "":

            new_filename = file.filename

            images_folder = os.path.join(
                app.root_path,
                "static",
                "images"
            )

            os.makedirs(images_folder, exist_ok=True)

            new_image_path = os.path.join(
                images_folder,
                new_filename
            )

            file.save(new_image_path)

            old_filename = os.path.basename(
                image["image_path"]
            )

            old_image_path = os.path.join(
                images_folder,
                old_filename
            )

            if os.path.exists(old_image_path):
                os.remove(old_image_path)

            cursor.execute("""
                UPDATE images
                SET
                    image_path = %s,
                    title = %s,
                    tags = %s,
                    description = %s,
                    category = %s
                WHERE id = %s
            """, (
                new_filename,
                title,
                tags,
                description,
                category,
                id
            ))

        else:

            cursor.execute("""
                UPDATE images
                SET
                    title = %s,
                    tags = %s,
                    description = %s,
                    category = %s
                WHERE id = %s
            """, (
                title,
                tags,
                description,
                category,
                id
            ))

        db.commit()

        cursor.close()
        db.close()

        if session.get("role") == "admin":

            return redirect(
                url_for("admin")
            )

        return redirect(
            url_for(
                "person",
                code=session["user_code"]
            )
        )

    cursor.close()
    db.close()

    return render_template(
        "edit_image.html",
        image=image
    )
    
@app.route("/delete-image/<int:id>", methods=["POST"])
def delete_image(id):

    if "user_code" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if session.get("role") == "admin":

        cursor.execute("""
            SELECT image_path
            FROM images
            WHERE id = %s
        """, (id,))

    else:

        cursor.execute("""
            SELECT image_path
            FROM images
            WHERE id = %s
            AND photographer_code = %s
        """, (
            id,
            session["user_code"]
        ))

    image = cursor.fetchone()

    if image is None:
        cursor.close()
        db.close()

        return "Image not found or access denied"

    images_folder = os.path.join(
        app.root_path,
        "static",
        "images"
    )

    filename = os.path.basename(
        image["image_path"]
    )

    image_file_path = os.path.join(
        images_folder,
        filename
    )

    if os.path.exists(image_file_path):
        os.remove(image_file_path)

    cursor.execute("""
        DELETE FROM images
        WHERE id = %s
    """, (id,))

    db.commit()

    cursor.close()
    db.close()

    if session.get("role") == "admin":

        return redirect(
            url_for("admin")
        )

    return redirect(
        url_for(
            "person",
            code=session["user_code"]
        )
    )
    
@app.route("/articles")
def articles():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    category = request.args.get("category")
    search = request.args.get("search")

    query = """
        SELECT
            articles.*,
            users.name AS writer_name
        FROM articles
        LEFT JOIN users
        ON articles.writer_code = users.code
        WHERE 1=1
    """

    values = []

    if category and category != "All":
        query += " AND articles.category=%s"
        values.append(category)

    if search:

        query += """
        AND (
            articles.title LIKE %s
            OR articles.keywords LIKE %s
            OR articles.content LIKE %s
        )
        """

        keyword = "%" + search + "%"

        values.extend([keyword, keyword, keyword])

    cursor.execute(query, values)

    articles = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM articles")

    categories = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "article.html",
        articles=articles,
        categories=categories,
        selected=category,
        search=search
    )

@app.route("/article/<int:id>")
def article_details(id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            articles.*,
            users.name AS writer_name,
            users.email AS writer_email
        FROM articles
        LEFT JOIN users
        ON articles.writer_code = users.code
        WHERE articles.id = %s
    """, (id,))

    article = cursor.fetchone()

    cursor.close()
    db.close()

    if article is None:
        return "Article not found"

    return render_template(
        "article_details.html",
        article=article
    )

@app.route("/upload-article", methods=["GET", "POST"])
def upload_article():

    # کاربر باید وارد حسابش شده باشد
    if "user_code" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        keywords = request.form["keywords"]
        content = request.form["content"]
        category = request.form["category"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO articles
            (
                content,
                keywords,
                title,
                category,
                writer_code
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            content,
            keywords,
            title,
            category,
            session["user_code"]
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "person",
                code=session["user_code"]
            )
        )

    return render_template("upload_article.html")

@app.route("/edit-article/<int:id>", methods=["GET", "POST"])
def edit_article(id):

    if "user_code" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if session.get("role") == "admin":

        cursor.execute("""
            SELECT *
            FROM articles
            WHERE id = %s
        """, (id,))

    else:

        cursor.execute("""
            SELECT *
            FROM articles
            WHERE id = %s
            AND writer_code = %s
        """, (
            id,
            session["user_code"]
        ))

    article = cursor.fetchone()

    if article is None:

        cursor.close()
        db.close()

        return "Article not found or access denied"

    if request.method == "POST":

        title = request.form["title"]
        keywords = request.form["keywords"]
        content = request.form["content"]
        category = request.form["category"]

        cursor.execute("""
            UPDATE articles
            SET
                title = %s,
                keywords = %s,
                content = %s,
                category = %s
            WHERE id = %s
        """, (
            title,
            keywords,
            content,
            category,
            id
        ))

        db.commit()

        cursor.close()
        db.close()

        if session.get("role") == "admin":

            return redirect(
                url_for("admin")
            )

        return redirect(
            url_for(
                "person",
                code=session["user_code"]
            )
        )

    cursor.close()
    db.close()

    return render_template(
        "edit_article.html",
        article=article
    )

@app.route("/delete-article/<int:id>", methods=["POST"])
def delete_article(id):

    if "user_code" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if session.get("role") == "admin":

        cursor.execute("""
            SELECT id
            FROM articles
            WHERE id = %s
        """, (id,))

    else:

        cursor.execute("""
            SELECT id
            FROM articles
            WHERE id = %s
            AND writer_code = %s
        """, (
            id,
            session["user_code"]
        ))

    article = cursor.fetchone()

    if article is None:

        cursor.close()
        db.close()

        return "Article not found or access denied"

    cursor.execute("""
        DELETE FROM articles
        WHERE id = %s
    """, (id,))

    db.commit()

    cursor.close()
    db.close()

    if session.get("role") == "admin":

        return redirect(
            url_for("admin")
        )

    return redirect(
        url_for(
            "person",
            code=session["user_code"]
        )
    )

@app.route("/writers")
def writers():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute("""

        SELECT

            users.code,
            users.name,
            users.email,

            COUNT(DISTINCT images.image_path) AS image_count,

            COUNT(DISTINCT articles.title) AS article_count

        FROM users

        LEFT JOIN images

        ON users.code = images.photographer_code

        LEFT JOIN articles

        ON users.code = articles.writer_code

        GROUP BY users.code

        ORDER BY users.name

    """)

    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "Writer-Photographer.html",
        users=users
    )
    
    
@app.route("/person/<code>")
def person(code):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT code,name,email
        FROM users
        WHERE code=%s
    """,(code,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM images
        WHERE photographer_code=%s
    """,(code,))
    images = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM articles
        WHERE writer_code=%s
    """,(code,))
    articles = cursor.fetchall()

    is_owner = (
    "user_code" in session
    and session["user_code"] == code)
    
    cursor.close()
    db.close()

    return render_template(
        "person.html",
        user=user,
        images=images,
        articles=articles,
        is_owner=is_owner
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run(debug=True)