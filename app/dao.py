from datetime import datetime

from flask_login import current_user
from sqlalchemy import distinct

from app.models import Class, Student, Account, Grade, Teacher, TeacherSubjectClass, Subject, Score, Semester, \
    Regulation
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


def get_teachers():
    return Teacher.query.all()


def get_semester():
    return Semester.query.all()


def get_classes_by_grade(grade_id):
    return Class.query.filter(Class.grade_id.__eq__(grade_id)).all()


def get_students_by_class(class_id):
    return Student.query.filter(Student.class_id.__eq__(class_id)).all()


def get_students(kw, class_id, page=None):
    students = Student.query

    if kw:
        pass

    if class_id:
        students = students.filter(Student.class_id.__eq__(class_id))

    if page:
        page = int(page)
        page_size = app.config['PAGE_SIZE']
        start = (page - 1) * page_size

        return students.slice(start, start + page_size)

    return students.all()


def count_student():
    return Student.query.count()


def get_user_by_id(user_id):
    return Account.query.get(user_id)


def auth_user(username, password):
    if username and password:
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

        return Account.query.filter(Account.username.__eq__(username),
                                    Account.password.__eq__(password)).first()


def add_user(username, password, **kwargs):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    user = Account(username=username.strip(),
                   password=password,
                   avatar=kwargs.get('avatar'))

    db.session.add(user)
    db.session.commit()


def input_score(student_id, subject_id, score_type, score_value, semester_id):
    existing_scores = Score.query.filter(Score.student_id == student_id, Score.subject_id == subject_id,
                                         Score.type == score_type, Score.semester_id == semester_id).count()
    if float(score_value) < 0 or float(score_value) > 10:
        return "Điểm phải nằm trong khoảng từ 0 tới 10."
    if score_type == '15 phút' and existing_scores >= 5:
        return "Không thể nhập quá 5 lần điểm 15 phút."
    elif score_type == '1 tiết' and existing_scores >= 3:
        return "Không thể nhập quá 3 lần điểm 1 tiết."
    elif score_type == 'Điểm thi' and existing_scores >= 1:
        return "Chỉ có thể nhập 1 lần điểm thi."

    new_score = Score(student_id=student_id, subject_id=subject_id, type=score_type, score=score_value,
                      semester_id=semester_id)

    db.session.add(new_score)
    db.session.commit()


def get_students_scores(class_id, subject_id, semester_id):
    # Lấy danh sách sinh viên trong lớp
    students = Student.query.filter(Student.class_id == class_id).all()

    students_scores = []
    for student in students:
        # Lấy điểm số của sinh viên cho môn học cụ thể
        scores = Score.query.filter(Score.student_id == student.id, Score.subject_id == subject_id,
                                    Score.semester_id == semester_id).all()

        score_dict = {
            "firstname": student.firstname,
            "lastname": student.lastname,
            "15 phút": [],
            "1 tiết": [],
            "Điểm thi": [],
            "semester": None
        }

        for score in scores:
            if len(score_dict[score.type]) < 5 and score.type == '15 phút':
                score_dict[score.type].append(score.score)
            elif len(score_dict[score.type]) < 3 and score.type == '1 tiết':
                score_dict[score.type].append(score.score)
            elif len(score_dict[score.type]) < 1 and score.type == 'Điểm thi':
                score_dict[score.type].append(score.score)

            score_dict["semester"] = str(score.semester)

        average_score = calculate_average_score(score_dict)
        score_dict["average"] = average_score
        score_dict["is_passing"] = is_student_passing(average_score)

        students_scores.append(score_dict)

    return students_scores


def calculate_average_score(score_dict):
    total_score = 0
    total_coefficient = 0

    if score_dict["15 phút"]:
        total_score += sum(score_dict["15 phút"]) * 1
        total_coefficient += len(score_dict["15 phút"]) * 1

    if score_dict["1 tiết"]:
        total_score += sum(score_dict["1 tiết"]) * 2
        total_coefficient += len(score_dict["1 tiết"]) * 2

    if score_dict["Điểm thi"]:
        total_score += sum(score_dict["Điểm thi"]) * 3
        total_coefficient += len(score_dict["Điểm thi"]) * 3

    if total_coefficient == 0:
        return None  # Tránh chia cho 0

    average_score = total_score / total_coefficient
    return round(average_score, 2)


def get_classes_and_subjects(teacher_id, semester_id):
    # Truy vấn cơ sở dữ liệu để lấy danh sách các lớp và môn học mà giáo viên đang dạy trong học kỳ
    classes_subjects = db.session.query(TeacherSubjectClass, Class, Subject).join(Class,
                                                                                  TeacherSubjectClass.class_id == Class.id).join(
        Subject, TeacherSubjectClass.subject_id == Subject.id).filter(
        TeacherSubjectClass.teacher_id == teacher_id).all()

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


def get_statistics(class_id, subject_id, semester_id):
    clas = Class.query.get(class_id)
    subject = Subject.query.get(subject_id)
    semester = Semester.query.get(semester_id)
    students_scores = get_students_scores(class_id, subject_id, semester_id)
    num_passed = sum(1 for s in students_scores if s['is_passing'])
    num_failed = len(students_scores) - num_passed
    pass_rate = round(num_passed / len(students_scores) * 100, 2) if students_scores else 0
    num_students = len(students_scores)
    return {
        'class': clas.name,
        'subject': subject.name,
        'semester': semester.name,
        'num_passed': num_passed,
        'num_failed': num_failed,
        'pass_rate': pass_rate,
        'num_students': num_students,
    }


# def student_view_scores():
#     student_id = current_user.id
#     student = Student.query.filter_by(id=student_id).first()
#     class_id = student.class_id
#     semesters = Semester.query.all()
#     subjects = Subject.query.all()
# 
#     scores_dict = {}
#     for semester in semesters:
#         for subject in subjects:
#             student_scores = get_students_scores(class_id, subject.id, semester.id)
#             for student_score in student_scores:
#                 if student_score["firstname"] == student.firstname and student_score["lastname"] == student.lastname:
#                     if semester.name not in scores_dict:
#                         scores_dict[semester.name] = {}
#                     if subject.name not in scores_dict[semester.name]:
#                         scores_dict[semester.name][subject.name] = {
#                             "15 phút": [],
#                             "1 tiết": [],
#                             "Điểm thi": []
#                         }
#                     for score_type in ["15 phút", "1 tiết", "Điểm thi"]:
#                         scores_dict[semester.name][subject.name][score_type].extend(student_score[score_type])
#
#     return scores_dict

