from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary
app = Flask(__name__)
app.secret_key = '!@!A@#WQEQ!@#WEQ!@#!#EWQWEQWE@!@#()(*^%$@!DFSDF'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:123456@localhost/studentdb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 20

db = SQLAlchemy(app=app)
login = LoginManager(app=app)

cloudinary.config(
    cloud_name='dvgpizkep',
    api_key='966854718195463',
    api_secret='OC5koTFjGtt4tPZ-VqqsLHWb6ME'
)