import enum
from datetime import datetime

from app import db, app
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin


class UserRoleEnum(enum.Enum):
    ADMIN = 1
    TEACHER = 2
    USER = 3


class Account(db.Model, UserMixin):
    __tablename__ = 'account'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(30), nullable=False, unique=True)
    password = Column(String(300), nullable=False)
    create_date = Column(DateTime, default=datetime.now())
    avatar = Column(String(200))
    status = Column(Boolean, default=True)
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER)
    student = relationship('Student', backref='account', uselist=False)
    teacher = relationship('Teacher', backref='account', uselist=False)
    regulation = relationship('Regulation', backref='account')

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


class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = Column(Integer, ForeignKey(Account.id), primary_key=True)
    firstname = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    address = Column(String(300), nullable=False)
    email = Column(String(100))
    dob = Column(Date)
    degree = Column(String(50), nullable=False)
    teachers_subjects_classes = relationship('TeacherSubjectClass', backref='teacher', lazy=True)

    def __str__(self):
        return self.lastname


class Class(db.Model):
    __tablename__ = 'class'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(10), nullable=False)
    quantity = Column(Integer, default=0)
    students = relationship('Student', backref='class', lazy=True)
    grade_id = Column(Integer, ForeignKey(Grade.id), nullable=False)
    teachers_subjects_classes = relationship('TeacherSubjectClass', backref='classes')

    def __str__(self):
        return self.name

class Student(db.Model):
    __tablename__ = 'student'
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    address = Column(String(300), nullable=False)
    email = Column(String(100))
    dob = Column(Date)
    date_join = Column(Date)
    scores = relationship('Score', backref='student', lazy=True)
    class_id = Column(Integer, ForeignKey(Class.id))
    account_id = Column(Integer, ForeignKey(Account.id))

    def __str__(self):
        return self.lastname


class Subject(db.Model):
    __tablename__ = 'subject'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    grade_id = Column(Integer, ForeignKey(Grade.id), nullable=False)
    scores = relationship('Score', backref='subject', lazy=True)
    teachers_subjects_classes = relationship('TeacherSubjectClass', backref='subject', lazy=True)

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


class Score(db.Model):
    __tablename__ = 'score'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey(Student.id), nullable=False)
    subject_id = Column(Integer, ForeignKey(Subject.id), nullable=False)
    type = Column(String(20), nullable=False)
    score = Column(Float, nullable=False)
    update_date = Column(DateTime, default=datetime.now())
    semester_id = Column(Integer, ForeignKey(Semester.id), nullable=False)


class TeacherSubjectClass(db.Model):
    __tablename__ = 'teacher_subject_class'
    teacher_id = Column(Integer, ForeignKey(Teacher.id), primary_key=True)
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
    admin_id = Column(Integer, ForeignKey(Account.id))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        import hashlib

        a = Account(username='admin', password=str(hashlib.md5('123456'.encode('utf-8')).hexdigest()),
                    user_role=UserRoleEnum.ADMIN)

        db.session.add(a)
        db.session.commit()
