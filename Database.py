import mysql.connector
import csv

# ================= DATABASE SETUP =================
def create_database():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR PASSWORD"
    )
    cursor = connection.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS db_class")
    cursor.close()
    connection.close()


def create_tables():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR PASSWORD",
        database="db_class"
    )
    cursor = connection.cursor()

    # USER
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        code VARCHAR(50) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100),
        password VARCHAR(255),
        role VARCHAR(20) DEFAULT 'user',
        work_field VARCHAR(100)
    )
    """)

    # IMAGES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        image_path VARCHAR(255) NOT NULL UNIQUE,
        title VARCHAR(100),
        tags VARCHAR(255),
        description TEXT,
        category VARCHAR(50),
        photographer_code VARCHAR(50),
        FOREIGN KEY (photographer_code) REFERENCES users(code)
    )
    """)

    # ARTICLES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        content TEXT NOT NULL,
        keywords VARCHAR(255),
        title VARCHAR(100),
        category VARCHAR(50),
        writer_code VARCHAR(50),
        FOREIGN KEY (writer_code) REFERENCES users(code),
        UNIQUE(title, writer_code)
    )
    """)

    connection.commit()
    cursor.close()
    connection.close()


# ================= MODELS =================
class User:
    def __init__(self, code, name, email, password=None, role="user", work_field=None):

        self.code = code
        self.name = name
        self.email = email
        self.password = password
        self.role = role
        self.work_field = work_field


class Image:
    def __init__(self, image_path, title, tags, description, category, photographer_code):
        self.image_path = image_path
        self.title = title
        self.tags = tags
        self.description = description
        self.category = category
        self.photographer_code = photographer_code


class Article:
    def __init__(self, content, keywords, title, category, writer_code):
        self.content = content
        self.keywords = keywords
        self.title = title
        self.category = category
        self.writer_code = writer_code


# ================= DATABASE CLASS =================
class Database:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="YOUR PASSWORD",
            database="db_class"
        )
        self.cursor = self.connection.cursor()

    def add_user(self, user):

        query = """
        INSERT INTO users
        (code, name, email, password, role, work_field)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name=name
        """

        self.cursor.execute(
            query,
            (
                user.code,
                user.name,
                user.email,
                user.password,
                user.role,
                user.work_field
            )
        )

        self.connection.commit()

    def add_image(self, image):

        query = """
        INSERT IGNORE INTO images
        (
            image_path,
            title,
            tags,
            description,
            category,
            photographer_code
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        data = (
            image.image_path,
            image.title,
            image.tags,
            image.description,
            image.category,
            image.photographer_code
        )

        self.cursor.execute(query, data)
        self.connection.commit()

    def add_article(self, article):

        query = """
        INSERT IGNORE INTO articles
        (content, keywords, title, category, writer_code)
        VALUES (%s,%s,%s,%s,%s)
        """

        data = (
            article.content,
            article.keywords,
            article.title,
            article.category,
            article.writer_code
        )

        self.cursor.execute(query, data)
        self.connection.commit()
        
    def close(self):
        self.cursor.close()
        self.connection.close()

# ================= CSV IMPORT =================
def import_articles(db):
    with open('articles.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            user = User(
                row['writer_code'],
                row['writer_name'],
                row['writer_email']
            )
            db.add_user(user)

            article = Article(
                row['content'],
                row['keywords'],
                row['title'],
                row['category'],
                row['writer_code']
            )
            db.add_article(article)


def import_images(db):
    with open('images.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            user = User(
                row['photographer_code'],
                row['photographer_name'],
                row['photographer_email']
            )
            db.add_user(user)

            image = Image(
                row['image_path'],
                row['title'],
                row['tags'],
                row['description'],
                row['category'],
                row['photographer_code']
            )
            db.add_image(image)


# ================= MAIN =================
if __name__ == "__main__":
    create_database()
    create_tables()

    db = Database()

    try:
        import_articles(db)
        print("Articles imported successfully")
    except Exception as e:
        print("Error importing articles:", e)

    try:
        import_images(db)
        print("Images imported successfully")
    except Exception as e:
        print("Error importing images:", e)

    db.close()