import hashlib
from datetime import datetime

import unidecode
from flask_admin.form import SecureForm, DateTimeField
from wtforms.validators import ValidationError

from app.models import Class, Grade, User, Subject, UserRoleEnum, Score, Semester, \
    Schedule, Regulation, ScoreType, Profile, RegulationHistory
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


class MyUserView(AuthenticatedAdmin):
    column_list = ['username', 'create_date', 'user_role', 'profile', 'status']
    form_base_class = SecureForm
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_labels = {
        'id': 'STT',
        'username': 'Tên tài khoản',
        'password': 'Mật khẩu',
        'create_date': 'Ngày tạo',
        'user_role': 'Vai trò',
        'profile': 'Họ tên',
        'status': 'Hoạt động'
    }
    form_columns = ['username', 'password', 'create_date', 'avatar', 'user_role', 'status']
    column_filters = ['username', 'profile']

    def on_model_change(self, form, model, is_created):
        if 'password' in form:
            password = form['password'].data
            hashed_password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
            model.password = hashed_password


class MyProfileView(AuthenticatedAdmin):
    column_list = ['id', 'firstname', 'lastname', 'gender', 'dob', 'user_id']
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_labels = {
        'id': 'STT',
        'firstname': 'Họ và tên đệm',
        'lastname': 'Tên',
        'gender': 'Giới tính',
        'address': 'Địa chỉ',
        'email': 'Email',
        'dob': 'Ngày sinh',
        'user_id': 'Tên tài khoản'
    }

    column_filters = ['firstname', 'lastname']
    column_exclude_list = ['user_id']

    def on_model_change(self, form, model, is_created):
        if is_created:
            if is_created:
                related_user = User.query.get(model.user_id)
                if related_user is not None and related_user.user_role == UserRoleEnum.STUDENT:
                    age = datetime.now().year - model.dob.year
                    regulation = Regulation.query.first()
                    if age < regulation.min_age or age > regulation.max_age:
                        raise ValidationError(
                            'Học sinh tiếp nhận phải có độ tuổi từ {} đến {}.'.format(regulation.min_age,
                                                                                      regulation.max_age))

                    num_students = User.query.filter_by(user_role=UserRoleEnum.STUDENT).count()
                    max_students = Regulation.query.first().max_students
                    if num_students >= max_students:
                        # Nếu đã tiếp nhận đủ số lượng học sinh, thông báo lỗi
                        raise ValidationError('Đã tiếp nhận đủ số lượng học sinh tối đa theo quy định.')

    def after_model_change(self, form, model, is_created):
        if is_created:
            # Nếu không có user nào được gán vào profile, tạo tài khoản mới cho học sinh
            if model.user_id is None:
                password = '123456'
                hashed_password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
                username = f'{model.lastname}{model.id}'
                username = remove_accents(username).lower().replace(" ", "")
                new_user = User(username=username, password=hashed_password, user_role=UserRoleEnum.STUDENT)
                db.session.add(new_user)
                db.session.commit()

                # Gán tài khoản mới cho học sinh
                model.user_id = new_user.id
                db.session.commit()
                # Nếu đã tiếp nhận đủ số lượng học sinh, tự động phân chia lớp
                dao.assign_students_to_classes()


class MyGradeView(AuthenticatedAdmin):
    column_list = ['id', 'name', 'classes']
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'id': 'STT',
        'name': 'Khối',
        'classes': 'Lớp học'
    }

    form_excluded_columns = ['subjects']
    column_filters = ['name']


class MyClassView(AuthenticatedAdmin):
    column_list = ['id', 'name', 'grade', 'quantity', 'users']
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'id': 'STT',
        'name': 'Tên lớp',
        'grade': 'Khối',
        'quantity': 'Sĩ số',
        'users': 'Học sinh'
    }

    form_excluded_columns = ['schedules', 'quantity']
    column_filters = ['name', 'grade']


class MySubjectView(AuthenticatedAdmin):
    column_list = ['id', 'name', 'grade']
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'id': 'STT',
        'name': 'Tên môn học',
        'grade': 'Khối'
    }

    form_excluded_columns = ['scores', 'schedules']
    column_filters = ['name', 'grade']


class MyScheduleView(AuthenticatedAdmin):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'user': 'Giáo viên',
        'subject': 'Môn học',
        'class': 'Lớp học',
        'start_date': 'Thời gian bắt đầu',
        'end_date': 'Thời gian kết thúc'
    }

    column_filters = ['user', 'subject', 'class']


class MyScoreView(AuthenticatedAdmin):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'user': 'Học sinh',
        'subject': 'Môn học',
        'semester': 'Học kì',
        'update_date': 'Thời gian cập nhật',
        'score': 'Điểm',
        'score_type': 'Loại điểm'
    }

    column_filters = ['user', 'subject', 'semester', 'score', 'score_type']


class MyScoreTypeView(AuthenticatedAdmin):
    column_list = ['id', 'name']
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_labels = {
        'id': 'STT',
        'name': 'Loại điểm'
    }

    form_excluded_columns = ['scores']
    column_filters = ['name']


class MySemesterView(AuthenticatedAdmin):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'name': 'Tên học kì',
        'year': 'Năm học'
    }

    form_excluded_columns = ['scores']
    column_filters = ['name', 'year']


def remove_accents(input_str):
    return unidecode.unidecode(input_str)


class MyRegulationView(AuthenticatedAdmin):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'id': 'STT',
        'min_age': 'Tuổi tiếp nhận tối thiểu',
        'max_age': 'Tuổi tiếp nhận tối đa',
        'max_class_size': 'Số lượng học sinh tối đa trong lớp',
        'max_students': 'Số lượng học sinh tiếp nhận tối đa'
    }

    form_excluded_columns = ['user']

    def on_model_change(self, form, regulation, is_created):
        # Khi một Regulation được tạo hoặc cập nhật, thêm một bản ghi vào RegulationHistory
        history = RegulationHistory(admin_id=current_user.id, regulation_id=regulation.id, update_date=datetime.now())
        db.session.add(history)


class MyRegulationHistoryView(AuthenticatedAdmin):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    column_labels = {
        'update_date': 'Thời gian cập nhật',
        'user': 'Người thay đổi',
        'regulation': 'Quy định thay đổi'
    }


class MyStatsView(AuthenticatedUser):
    @expose("/", methods=['GET', 'POST'])
    def index(self):
        subjects = dao.get_subjects()  # Lấy danh sách môn học
        semesters = dao.get_semester()  # Lấy danh sách học kỳ
        if request.method == 'POST':
            subject_id = request.form.get('subject_id')  # Lấy id của môn học từ form
            semester_id = request.form.get('semester_id')  # Lấy id của học kỳ từ form

            statistics = dao.get_statistics(subject_id=subject_id, semester_id=semester_id)
            return self.render('admin/statistics.html', stats=statistics, subjects=subjects,
                               semesters=semesters)

        return self.render('admin/statistics.html', subjects=subjects,
                           semesters=semesters)


class LogoutView(AuthenticatedUser):
    @expose("/")
    def index(self):
        logout_user()
        return redirect('/admin')


# Quản lý người dùng
admin.add_view(MyUserView(User, db.session, name='Quản lý tài khoản', category='Quản lý người dùng'))
admin.add_view(MyProfileView(Profile, db.session, name='Quản lý thông tin', category='Quản lý người dùng'))

# Quản lý học tập
admin.add_view(MySemesterView(Semester, db.session, name='Quản lý học kì', category='Quản lý học tập'))
admin.add_view(MyGradeView(Grade, db.session, name='Quản lý khối lớp', category='Quản lý học tập'))
admin.add_view(MyClassView(Class, db.session, name='Quản lý lớp', category='Quản lý học tập'))
admin.add_view(MySubjectView(Subject, db.session, name='Quản lý môn học', category='Quản lý học tập'))
admin.add_view(MyScheduleView(Schedule, db.session, name='Quản lý lịch dạy', category='Quản lý học tập'))
admin.add_view(MyScoreTypeView(ScoreType, db.session, name='Quản lý loại điểm', category='Quản lý học tập'))
admin.add_view(MyScoreView(Score, db.session, name='Quản lý điểm', category='Quản lý học tập'))

# Quản lý quy định
admin.add_view(MyRegulationView(Regulation, db.session, name='Thay đổi quy định', category='Quản lý quy định'))
admin.add_view(
    MyRegulationHistoryView(RegulationHistory, db.session, name='Lịch sử thay đổi', category='Quản lý quy định'))

# Thống kê và báo cáo
admin.add_view(MyStatsView(name='Thống kê báo cáo'))

# Đăng xuất
admin.add_view(LogoutView(name='Đăng xuất'))
