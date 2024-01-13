import enum
from datetime import datetime

from app import db, app
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin


class UserRoleEnum(enum.Enum):
    ADMIN = 1
    TEACHER = 2
    STUDENT = 3


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(30), nullable=False, unique=True)
    password = Column(String(300), nullable=False)
    create_date = Column(DateTime, default=datetime.now())
    avatar = Column(String(200))
    status = Column(Boolean, default=True)
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.STUDENT)
    profile = relationship('Profile', backref='user', uselist=False)
    regulation = relationship('RegulationHistory', backref='user')
    scores = relationship('Score', backref='user', lazy=True)
    schedules = relationship('Schedule', backref='user', lazy=True)
    class_id = Column(Integer, ForeignKey('class.id'))

    def __str__(self):
        return self.username


class Grade(db.Model):
    __tablename__ = 'grade'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    classes = relationship("Class", backref='grade', lazy=True)
    subjects = relationship('Subject', backref='grade', lazy=True)

    def __str__(self):
        return self.name


class Class(db.Model):
    __tablename__ = 'class'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(10), nullable=False)
    quantity = Column(Integer, default=0)
    grade_id = Column(Integer, ForeignKey(Grade.id), nullable=False)
    users = relationship('User', backref='class', lazy=True)
    schedules = relationship('Schedule', backref='class', lazy=True)

    def __str__(self):
        return self.name


class Profile(db.Model):
    __tablename__ = 'profile'
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    address = Column(String(300), nullable=False)
    email = Column(String(100))
    dob = Column(Date)
    user_id = Column(Integer, ForeignKey(User.id))

    def __str__(self):
        return self.lastname


class Subject(db.Model):
    __tablename__ = 'subject'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    scores = relationship('Score', backref='subject', lazy=True)
    schedules = relationship('Schedule', backref='subject', lazy=True)
    grade_id = Column(Integer, ForeignKey(Grade.id), nullable=False)

    def __str__(self):
        return self.name


class Semester(db.Model):
    __tablename = 'semester'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False)
    scores = relationship('Score', backref='semester', lazy=True)

    def __str__(self):
        return f'{self.name}-{self.year}'


class ScoreType(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    scores = relationship('Score', backref='score_type', lazy=True)

    def __str__(self):
        return self.name


class Score(db.Model):
    __tablename__ = 'score'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    subject_id = Column(Integer, ForeignKey(Subject.id), nullable=False)
    semester_id = Column(Integer, ForeignKey(Semester.id), nullable=False)
    type_id = Column(Integer, ForeignKey(ScoreType.id), nullable=False)
    score = Column(Float, nullable=False)
    update_date = Column(DateTime, default=datetime.now())


class Schedule(db.Model):
    __tablename__ = 'schedule'
    user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
    subject_id = Column(Integer, ForeignKey(Subject.id), primary_key=True)
    class_id = Column(Integer, ForeignKey(Class.id), primary_key=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)


class Regulation(db.Model):
    __tablename__ = 'regulation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    min_age = Column(Integer, nullable=False)
    max_age = Column(Integer, nullable=False)
    max_class_size = Column(Integer, nullable=False)
    max_students = Column(Integer, default=1000, nullable=False)
    user = relationship("RegulationHistory", backref="regulation")


class RegulationHistory(db.Model):
    __tablename__ = 'regulation_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey(User.id))
    regulation_id = Column(Integer, ForeignKey(Regulation.id))
    update_date = Column(DateTime, default=datetime.now())


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        import hashlib

        a = User(username='admin', password=str(hashlib.md5('123456'.encode('utf-8')).hexdigest()),
                 user_role=UserRoleEnum.ADMIN)

        db.session.add(a)
        db.session.commit()
