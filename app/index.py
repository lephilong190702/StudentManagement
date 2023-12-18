import math

from flask import render_template, request, redirect, url_for, flash
import dao
from app import app, login
from flask_login import login_user, logout_user, current_user, login_required
import cloudinary.uploader

from app.models import Class, Teacher, UserRoleEnum


@app.route("/")
def index():
    kw = request.args.get("kw")
    class_id = request.args.get('class_id')
    grade_id = request.args.get('grade_id')
    page = request.args.get('page')

    grads = dao.get_grades()
    clas = dao.get_classes_by_grade(grade_id)
    studs = dao.get_students(kw, class_id, page)
    num = dao.count_student()
    page_size = app.config['PAGE_SIZE']

    return render_template("index.html", classes=clas,
                           students=studs, grades=grads, pages=math.ceil(num / page_size))


@app.route("/about")
def about_page():
    return render_template("about.html")


@app.context_processor
def utility_functions():
    def get_classes_by_grade(grade_id):
        return Class.query.filter(Class.grade_id == grade_id).all()

    return {
        'grades': dao.get_grades(),
        'get_classes_by_grade': get_classes_by_grade
    }


@app.route("/classes/<int:class_id>")
def class_detail(class_id):
    kw = request.args.get("kw")
    cla = dao.get_class_by_id(class_id)
    studs = dao.get_students_by_class(class_id)
    return render_template("class_detail.html", students=studs, class_info=cla)


@app.route('/manage_scores', methods=['GET', 'POST'])
def manage_scores():
    if current_user.is_authenticated and current_user.user_role == UserRoleEnum.TEACHER:
        if request.method == 'POST':
            # Lấy học kỳ từ form
            semester_id = request.form.get('semester_id')

            # Chuyển hướng đến trang hiển thị các lớp và môn học
            return redirect(url_for('teacher_dashboard', semester_id=semester_id))
        semesters = dao.get_semester()
    else:
        return redirect(url_for('user_login'))

    return render_template('manage_scores.html', semesters=semesters)


@app.route('/teacher_dashboard/<semester_id>')
def teacher_dashboard(semester_id):
    # Lấy danh sách các lớp và môn học trong học kỳ này
    classes_subjects = dao.get_classes_and_subjects(current_user.id, semester_id)

    # Hiển thị trang cho học kỳ này
    return render_template('teacher_dashboard.html', classes_subjects=classes_subjects)


@app.route('/input_scores/<class_id>/<subject_id>/<semester_id>', methods=['GET', 'POST'])
def input_scores(class_id, subject_id, semester_id):
    if request.method == 'POST':
        # Lấy thông tin từ form
        student_id = request.form.get('student_id')
        score_type = request.form.get('score_type')
        score_value = request.form.get('score_value')

        message = dao.input_score(student_id=student_id, score_type=score_type, score_value=score_value,
                                  subject_id=subject_id, semester_id=semester_id)
        if message:
            flash(message)
            return redirect(url_for('input_scores', class_id=class_id, subject_id=subject_id, semester_id=semester_id))
        return redirect(url_for('teacher_dashboard', semester_id=semester_id))

    # Lấy danh sách sinh viên trong lớp
    students = dao.get_students_by_class(class_id)
    semests = dao.get_semester()
    return render_template('input_scores.html', students=students, semesters=semests)


@app.route('/view_scores/<class_id>/<subject_id>/<semester_id>', methods=['GET'])
def view_scores(class_id, subject_id, semester_id):
    students_scores = dao.get_students_scores(class_id, subject_id, semester_id=semester_id)
    return render_template('view_scores.html', scores=students_scores)


@app.route("/teachers")
def load_teachers():
    teachs = dao.get_teachers()
    return render_template("teachers.html", teachers=teachs)


@app.route("/user_register", methods=['get', 'post'])
def user_register():
    err_msg = ""
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        avatar_path = None
        try:
            if password.strip().__eq__(confirm.strip()):
                avatar = request.files.get('avatar')
                if avatar:
                    res = cloudinary.uploader.upload(avatar)
                    avatar_path = res['secure_url']
                    print("Avatar path:", avatar_path)
                else:
                    print("Error")
                dao.add_user(username=username, password=password, avatar=avatar_path)
                return redirect(url_for('index'))
            else:
                err_msg = 'Mật khẩu xác nhận không khớp!!'
        except Exception as ex:
            err_msg = 'Lỗi ' + str(ex)

    return render_template('register.html', err_msg=err_msg)


@app.route('/user_login', methods=['get', 'post'])
def user_login():
    err_msg = ''
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')

        user = dao.auth_user(username=username, password=password)
        if user:
            login_user(user=user)
            return redirect(url_for('index'))
        else:
            err_msg = 'Username hoặc password không hợp lệ!!'
    return render_template('login.html')


@app.route("/user_logout")
def user_logout():
    logout_user()
    return redirect(url_for('user_login'))


@app.route("/admin/login", methods=['post'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = dao.auth_user(username=username, password=password)
    if user:
        login_user(user)

    return redirect("/admin")


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == "__main__":
    from app import admin

    app.run(debug=True)
