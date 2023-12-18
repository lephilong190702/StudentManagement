import hashlib
from datetime import date

from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import SecureForm, DateTimeField
from sqlalchemy import event
from sqlalchemy.event import listens_for
from sqlalchemy.orm import sessionmaker
from wtforms.fields.simple import StringField
from wtforms.form import Form

from app.models import Class, Student, Grade, Teacher, Account, Subject, UserRoleEnum, Score, Semester, \
    TeacherSubjectClass, Regulation
from app import app, db, dao
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import logout_user, current_user
from flask import redirect, flash, request

admin = Admin(app=app, name="QUẢN LÝ HỌC SINH", template_mode='bootstrap4')


class AuthenticatedAdmin(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRoleEnum.ADMIN


class AuthenticatedUser(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated


class MyAccountView(AuthenticatedAdmin):
    column_list = ['username', 'create_date', 'user_role']
    form_base_class = SecureForm

    def on_model_change(self, form, model, is_created):
        if 'password' in form:
            password = form['password'].data
            hashed_password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
            model.password = hashed_password


# class MyUserView(AuthenticatedAdmin):
#     column_list = ['id', 'firstname', 'lastname', 'gender', 'account']
#     form_excluded_columns = ['student', 'teacher']
#     can_export = True

class TeacherForm(Form):
    account = QuerySelectField(query_factory=lambda: db.session.query(Account), allow_blank=True)
    firstname = StringField('First Name')
    lastname = StringField('Last Name')
    gender = StringField('Gender')
    address = StringField('Address')
    degree = StringField('Degree')


class MyTeacherView(AuthenticatedAdmin):
    form = TeacherForm
    column_list = ['firstname', 'lastname', 'gender', 'degree', 'teachers_subjects_classes']

    def on_model_change(self, form, Teacher, is_created):
        if is_created:
            Teacher.id = form.account.data.id
        super().on_model_change(form, Teacher, is_created)

    can_export = True


class MyStudentView(AuthenticatedAdmin):
    # column_list = ['id', 'lastname', 'class']
    # can_export = True
    #
    # def on_model_change(self, form, model, is_created):
    #     if is_created:
    #         today = date.today()
    #         age = today.year - model.dob.year - ((today.month, today.day) < (model.dob.month, model.dob.day))
    #         if age < 15 or age > 20:
    #             raise ValueError("The student's age must be between 15 and 20 years old.")
    #         # Get the list of classes sorted by their current quantity
    #         classes = Class.query.filter(Class.grade_id == 1).order_by(Class.quantity.desc()).all()
    #
    #         # Find a class with less than 40 students
    #         for cls in classes:
    #             if cls.quantity < 4:
    #                 model.class_id = cls.id  # Assign the student to the class
    #                 cls.quantity += 1  # Update the quantity of the class
    #                 db.session.commit()
    #                 return
    #
    #         # If no class is found, raise an exception or handle it as needed
    #         raise Exception("All classes are full.")
    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        regulation = dao.get_current_regulation()

        form = self.create_form()
        if self.validate_form(form):
            age = dao.calculate_age(form.dob.data)
            if age < regulation.min_age or age > regulation.max_age:
                flash("Độ tuổi học sinh tiếp nhận phải từ 15 tới 20.", 'error')
                return self.render('admin/model/create.html', form=form)

        return super(MyStudentView, self).create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        # Get the current regulations
        regulation = dao.get_current_regulation()

        if request.method == 'POST':
            form = self.edit_form()
            if self.validate_form(form):
                # Check the student's age against the regulations
                age = dao.calculate_age(form.dob.data)  # assuming you have a function to calculate age
                if age < regulation.min_age or age > regulation.max_age:
                    flash("Độ tuổi học sinh tiếp nhận phải từ 15 tới 20.", 'error')
                    return self.render('admin/model/edit.html', form=form)
        return super(MyStudentView, self).edit_view()

class MyClassView(AuthenticatedAdmin):
    column_list = ['id', 'teacher', 'name', 'students', 'grade', 'quantity']


class MyRegulationView(AuthenticatedAdmin):
    can_export = True


class MyTeacherSubjectClassView(AuthenticatedAdmin):
    column_exclude_list = ['start_date', 'end_date']
    can_export = True


class MyGradeView(AuthenticatedAdmin):
    column_list = ['id', 'name']
    can_export = True


class MySubjectView(AuthenticatedAdmin):
    can_export = True


class MyScoreView(AuthenticatedAdmin):
    can_export = True


class MyStatsView(AuthenticatedUser):
    @expose("/", methods=['GET', 'POST'])
    def index(self):
        subjects = dao.get_subjects()  # Lấy danh sách môn học
        semesters = dao.get_semester()  # Lấy danh sách học kỳ

        if request.method == 'POST':
            subject_id = request.form.get('subject_id')  # Lấy id của môn học từ form
            semester_id = request.form.get('semester_id')  # Lấy id của học kỳ từ form

            classes = dao.get_classes()
            statistics = []
            for class_ in classes:
                statistic = dao.get_statistics(class_.id, subject_id, semester_id)
                statistics.append(statistic)

            return self.render('admin/statistics.html', statistics=statistics, subjects=subjects, semesters=semesters)

        return self.render('admin/statistics.html', subjects=subjects, semesters=semesters)




class MySemesterView(AuthenticatedAdmin):
    can_export = True


class LogoutView(AuthenticatedUser):
    @expose("/")
    def index(self):
        logout_user()
        return redirect('/admin')


admin.add_view(MyAccountView(Account, db.session, name='Quản lý tài khoản'))
# admin.add_view(MyUserView(User, db.session, name='Người dùng'))
admin.add_view(MyTeacherView(Teacher, db.session, name='Quản lý giáo viên'))
admin.add_view(MyStudentView(Student, db.session, name='Quản lý học sinh'))
admin.add_view(MyGradeView(Grade, db.session, name='Quản lý khối lớp'))
admin.add_view(MyClassView(Class, db.session, name='Quản lý lớp'))
admin.add_view(MySubjectView(Subject, db.session, name='Quản lý môn học'))
admin.add_view(MySemesterView(Semester, db.session, name='Quản lý học kì'))
admin.add_view(MyTeacherSubjectClassView(TeacherSubjectClass, db.session, name='Quản lý lịch dạy'))
admin.add_view(MyScoreView(Score, db.session, name='Quản lý điểm'))
admin.add_view(MyRegulationView(Regulation, db.session, name='Thay đổi quy định'))
admin.add_view(MyStatsView(name='Thống kê báo cáo'))
admin.add_view(LogoutView(name='Đăng xuất'))
