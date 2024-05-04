# Brody Banner, Matthew Rinaldi

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import calendar
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'
# Couldn't get random key working
app.config['SECRET_KEY'] = 'bruhevent!'
db = SQLAlchemy(app)
bootstrap = Bootstrap(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

assignments_schedules = db.Table('assignments_schedules',
    db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'), primary_key=True),
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id'), primary_key=True)
)

class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    password = db.Column(db.String(40), nullable=False)
    assignments = db.relationship('Assignment', backref='student', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='student', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return '<Student %r>' % self.id

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(40), nullable=False)
    due = db.Column(db.DateTime, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    
    def __repr__(self):
        return '<Assignment %r>' % self.id

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(40), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    assignments = db.relationship('Assignment', secondary=assignments_schedules, backref=db.backref('schedules', lazy=True))

    def __repr__(self):
        return '<Schedule %r>' % self.id
    
@login_manager.user_loader
def load_user(user_id):
    return Student.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        existing_user = Student.query.filter_by(name=name).first()
        if existing_user:
            flash('User already exists. Please log in.')
            return redirect(url_for('login'))
        new_user = Student(name=name, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('You have successfully signed up! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        user = Student.query.filter_by(name=name).first()
        if user and user.password == password:
            login_user(user)
            current_month = datetime.now().month
            month_url = url_for('month', month=current_month)
            return redirect(month_url)
        else:
            flash('Invalid username or password. Please try again.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        return redirect('/login')
    except Exception as e:
        db.session.rollback()
        print(e)
        return 'Failed to delete user.'

def calculate_combined_weight(month):
    combined_weights = {}

    assignments = Assignment.query.filter(
        db.extract('month', Assignment.due) == month,
        Assignment.student_id == current_user.id
    ).all()

    schedules = Schedule.query.filter(
        db.extract('month', Schedule.start_date) <= month,
        db.extract('month', Schedule.end_date) >= month,
        Schedule.student_id == current_user.id
    ).all()

    for day in range(1, calendar.monthrange(2024, month)[1] + 1):
        combined_weight = 0
        
        for assignment in assignments:
            if assignment.due.day == day:
                combined_weight += assignment.weight
        
        for schedule in schedules:
            if schedule.start_date.day <= day <= schedule.end_date.day:
                combined_weight += schedule.weight
        
        combined_weights[day] = combined_weight
    
    return combined_weights

@app.route('/month/<int:month>')
@login_required
def month(month):
    month_name = calendar.month_name[month]
    start_day = calendar.monthrange(2024, month)[0] + 1
    num_days = calendar.monthrange(2024, month)[1]
    combined_weights = calculate_combined_weight(month)

    return render_template('month.html', month_name=month_name, num_days=num_days, month=month, start_day=start_day, combined_weights=combined_weights)

@app.route('/day/<int:month>/<int:day>', methods=['POST', 'GET'])
@login_required
def day(month, day):
    month_name = calendar.month_name[month]
    year = datetime.now().year
    start_day = calendar.monthrange(2024, month)[0] + 1
    day_name = calendar.day_name[((day + start_day) % 7) - 2]

    assignments = Assignment.query.filter(
        db.extract('month', Assignment.due) == month,
        db.extract('day', Assignment.due) == day,
        Assignment.student_id == current_user.id
    ).order_by(Assignment.due).all()

    return render_template('day.html', month_name=month_name, day_name=day_name, day=day, month=month, year=year, assignments=assignments)

@app.route('/year')
@login_required
def year():
    months = {i: calendar.month_name[i] for i in range(1, 13)}
    return render_template('year.html', months=months)

@app.route('/assignment')
@login_required
def assignment():
    assignments = Assignment.query.filter_by(student_id=current_user.id).order_by(Assignment.due).all()
    return render_template('assignment.html', assignments=assignments)

@app.route('/schedules')
@login_required
def schedules():
    schedules = Schedule.query.all()
    return render_template('schedules.html')

@app.route('/account')
@login_required
def account():
    return render_template('account.html', current_user=current_user)

@app.route('/add', methods=['POST'])
def add_assignment():
    assignment_title = request.form['title']
    assignment_description = request.form['description']
    assignment_weight = request.form['weight']

    # Datetime conversion
    try:
        assignment_date = request.form['date']
        assignment_time = request.form['time']

        date_obj = datetime.strptime(assignment_date, '%Y-%m-%d')
        time_obj = datetime.strptime(assignment_time, '%H:%M')
        assignment_datetime = datetime(
            date_obj.year,
            date_obj.month,
            date_obj.day,
            time_obj.hour,
            time_obj.minute
        )
    except Exception as e:
        print(e)
        return 'Failed DateTime conversion'

    new_assignment = Assignment(title=assignment_title, due=assignment_datetime, weight=assignment_weight, desc=assignment_description, student_id=current_user.id)

    try:
        db.session.add(new_assignment)
        db.session.commit()
        return redirect(request.form['redirect_url'])
    except Exception as e:
        print(e)
        return 'Failed to add assignment.'
    

@app.route('/delete', methods=['POST'])
def delete_assignment():
    assignment_id = request.form['assignment_id']
    try:
        db.session.delete(Assignment.query.get(assignment_id))
        db.session.commit()
        return redirect('/assignment')
    except Exception as e:
        print(e)
        return 'Failed to delete assignment.'

def create_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_db()
    app.run(debug=True)