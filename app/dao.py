import random
from datetime import datetime, date

from flask_login import current_user
from sqlalchemy import distinct, func, case, Float, Numeric

from app.models import Class, User, Grade, Schedule, Subject, Score, Semester, \
    Regulation, UserRoleEnum, ScoreType
from app import app, db
import hashlib


def get_classes():
    return Class.query.all()


def get_class_by_id(class_id):
    return Class.query.get(class_id)


def get_grades():
    return Grade.query.all()


def get_subjects():
    return Subject.query.all()


def get_score_type():
    return ScoreType.query.all()


def get_teachers():
    return User.query.filter_by(user_role=UserRoleEnum.TEACHER).all()


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_semester():
    return Semester.query.all()


def get_classes_by_grade(grade_id):
    return Class.query.filter(Class.grade_id.__eq__(grade_id)).all()


def get_students_by_class(class_id):
    return User.query.filter_by(user_role=UserRoleEnum.STUDENT, class_id=class_id).all()


def get_students(kw, class_id, page=None):
    students = User.query.filter_by(user_role=UserRoleEnum.STUDENT)

    if kw:
        pass

    if class_id:
        students = students.filter(User.class_id.__eq__(class_id))

    if page:
        page = int(page)
        page_size = app.config['PAGE_SIZE']
        start = (page - 1) * page_size

        return students.slice(start, start + page_size)

    return students.all()


def count_student():
    return User.query.filter_by(user_role=UserRoleEnum.STUDENT).count()


def auth_user(username, password):
    if username and password:
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

        return User.query.filter(User.username.__eq__(username),
                                 User.password.__eq__(password)).first()


def add_user(username, password, **kwargs):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    user = User(username=username.strip(),
                password=password,
                avatar=kwargs.get('avatar'))

    db.session.add(user)
    db.session.commit()


def change_password(user, new_password):
    hashed_password = str(hashlib.md5(new_password.strip().encode('utf-8')).hexdigest())
    user.password = hashed_password
    db.session.commit()


def input_score(student_id, subject_id, type_id, score_value, semester_id):
    # Kiểm tra xem điểm có nằm trong khoảng từ 0 tới 10 không
    if float(score_value) < 0 or float(score_value) > 10:
        return "Điểm phải nằm trong khoảng từ 0 tới 10."

    # Lấy loại điểm từ cơ sở dữ liệu
    score_type = ScoreType.query.get(type_id)
    if score_type is None:
        return "Loại điểm không tồn tại."

    score_type_name = score_type.name

    # Kiểm tra số lượng điểm hiện tại
    existing_scores = Score.query.filter(Score.user_id == student_id, Score.subject_id == subject_id,
                                         Score.type_id == type_id, Score.semester_id == semester_id).count()
    if score_type_name == '15 phút' and existing_scores >= 5:
        return "Không thể nhập quá 5 lần điểm 15 phút."
    elif score_type_name == '1 tiết' and existing_scores >= 3:
        return "Không thể nhập quá 3 lần điểm 1 tiết."
    elif score_type_name == 'Điểm thi' and existing_scores >= 1:
        return "Chỉ có thể nhập 1 lần điểm thi."

    # Tạo và lưu điểm mới
    new_score = Score(user_id=student_id, subject_id=subject_id, type_id=type_id, score=score_value,
                      semester_id=semester_id)

    db.session.add(new_score)
    db.session.commit()


def get_students_scores(class_id, subject_id, semester_id):
    # Lấy danh sách điểm số của sinh viên cho môn học cụ thể
    scores = db.session.query(User, Score, ScoreType, Semester).join(
        Score, User.id == Score.user_id
    ).join(
        ScoreType, Score.type_id == ScoreType.id
    ).join(
        Semester, Score.semester_id == Semester.id
    ).filter(
        User.class_id == class_id,
        Score.subject_id == subject_id,
        Score.semester_id == semester_id
    ).all()

    # Tạo một từ điển để lưu trữ điểm số của mỗi học sinh
    students_scores = {}

    for user, score, score_type, semester in scores:
        # Nếu học sinh chưa có trong từ điển, thêm họ vào
        if user.id not in students_scores:
            students_scores[user.id] = {
                "id": user.id,
                "firstname": user.profile.firstname,
                "lastname": user.profile.lastname,
                "15 phút": [],
                "1 tiết": [],
                "Điểm thi": [],
                "semester": str(semester)
            }

        # Thêm điểm vào danh sách điểm tương ứng của học sinh
        students_scores[user.id][score_type.name].append(score.score)

    # Chuyển từ điển thành danh sách để dễ dàng sử dụng trong template
    students_scores_list = list(students_scores.values())

    # Tính điểm trung bình cho mỗi học sinh
    for score_dict in students_scores_list:
        average_score = calculate_average_score(score_dict)
        score_dict["average"] = average_score
        score_dict["is_passing"] = is_student_passing(average_score)

    return students_scores_list


def calculate_average_score(score_dict):
    total_score = 0
    total_coefficient = 0

    for score_type, scores in score_dict.items():
        if score_type in ["15 phút", "1 tiết", "Điểm thi"]:
            coefficient = 1 if score_type == "15 phút" else 2 if score_type == "1 tiết" else 3
            total_score += sum(scores) * coefficient
            total_coefficient += len(scores) * coefficient

    if total_coefficient == 0:
        return None  # Tránh chia cho 0

    average_score = total_score / total_coefficient
    return round(average_score, 2)


def get_classes_and_subjects(teacher_id, semester_id):
    # Truy vấn cơ sở dữ liệu để lấy danh sách các lớp và môn học mà giáo viên đang dạy trong học kỳ
    classes_subjects = db.session.query(Schedule, Class, Subject).join(Class,
                                                                       Schedule.class_id == Class.id).join(
        Subject, Schedule.subject_id == Subject.id).filter(
        Schedule.user_id == teacher_id).all()

    # Chuyển đổi kết quả truy vấn thành danh sách các từ điển
    classes_subjects_list = []
    for record in classes_subjects:
        classes_subjects_list.append({
            "class_id": record.Class.id,
            "class_name": record.Class.name,
            "subject_id": record.Subject.id,
            "subject_name": record.Subject.name,
            "semester_id": semester_id
        })

    return classes_subjects_list


def get_current_regulation():
    return Regulation.query.order_by(Regulation.id.desc()).first()


def calculate_age(birth_date):
    today = datetime.today()
    age = today.year - birth_date.year

    # if birth date has not occurred this year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age


def is_student_passing(average_score):
    if average_score is None:
        return False  # hoặc trả về giá trị mặc định khác tùy thuộc vào yêu cầu của bạn
    return average_score >= 5


def get_statistics(subject_id, semester_id):
    student_scores = db.session.query(
        User.id.label('user_id'),
        ((func.sum(case((ScoreType.name == '15 phút', Score.score), else_=0))
          + 2 * func.sum(case((ScoreType.name == '1 tiết', Score.score), else_=0))
          + 3 * func.sum(case((ScoreType.name == 'Điểm thi', Score.score), else_=0)))
         / (func.sum(case((ScoreType.name == '15 phút', 1), else_=0))
            + 2 * func.sum(case((ScoreType.name == '1 tiết', 1), else_=0))
            + 3 * func.sum(case((ScoreType.name == 'Điểm thi', 1), else_=0)))).label('average_score')
    ).join(Score).join(ScoreType, Score.type_id == ScoreType.id).filter(
        Score.subject_id == subject_id, Score.semester_id == semester_id).group_by(User.id).subquery()

    average_scores_query = db.session.query(student_scores).select_from(student_scores)
    for row in average_scores_query:
        print(f'user_id: {row.user_id}, average_score: {row.average_score}')

    return db.session.query(
        Class.name.label('class_name'),
        func.count(User.id).label('total_students'),
        func.sum(case((student_scores.c.average_score >= 5, 1), else_=0)).label('number_passed'),
    ).join(User).join(student_scores, User.id == student_scores.c.user_id).group_by(Class.name).add_columns(
        (func.sum(case((student_scores.c.average_score >= 5, 1), else_=0)) / func.cast(func.count(User.id),
                                                                                       Float) * 100).label('pass_rate'))


def assign_students_to_classes():
    # Lấy danh sách tất cả học sinh chưa có lớp
    students = User.query.filter_by(user_role=UserRoleEnum.STUDENT, class_id=None).all()
    # Lấy max_class_size từ Regulation
    max_class_size = Regulation.query.first().max_class_size
    # Lấy danh sách tất cả lớp
    classes = Class.query.all()
    # Xáo trộn danh sách học sinh
    random.shuffle(students)
    # Phân chia học sinh vào các lớp
    for student in students:
        # Tìm lớp hiện tại có ít học sinh nhất và chưa đạt max_class_size
        min_class = min([c for c in classes if c.quantity < max_class_size], key=lambda x: x.quantity, default=None)
        if min_class is None:
            # Nếu không tìm thấy lớp nào, tạo một lớp mới
            new_class = Class(name=f'10A{len(classes) + 1}', quantity=0, grade_id=1)
            db.session.add(new_class)
            db.session.commit()
            classes.append(new_class)
            min_class = new_class
        student.class_id = min_class.id
        min_class.quantity += 1
    db.session.commit()


def get_scores(user_id):
    return Score.query.filter_by(user_id=user_id).all()


def get_scores_by_semester(scores):
    scores_by_semester = {}
    for score in scores:
        if score.semester.name not in scores_by_semester:
            scores_by_semester[score.semester.name] = {}
        if score.subject.name not in scores_by_semester[score.semester.name]:
            scores_by_semester[score.semester.name][score.subject.name] = {}
        if score.score_type.name not in scores_by_semester[score.semester.name][score.subject.name]:
            scores_by_semester[score.semester.name][score.subject.name][score.score_type.name] = []
        scores_by_semester[score.semester.name][score.subject.name][score.score_type.name].append(score.score)
    return scores_by_semester


def calculate_semester_averages(scores_by_semester):
    semester_averages = {}
    for semester, subjects in scores_by_semester.items():
        total_score = 0
        total_subjects = 0
        for subject, score_types in subjects.items():
            subject_average = calculate_average_score(score_types)
            scores_by_semester[semester][subject]['Điểm trung bình'] = subject_average
            if subject_average is not None:
                total_score += subject_average
                total_subjects += 1
        if total_subjects > 0:
            semester_averages[semester] = round(total_score / total_subjects, 2)
    return semester_averages
