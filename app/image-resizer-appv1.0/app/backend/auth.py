from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    if not all([email, password, firstname, lastname]):
        return jsonify({'error': 'All fields required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    user = User(email=email, firstname=firstname, lastname=lastname)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Registration successful'}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'message': 'Login successful', 'firstname': user.firstname, 'lastname': user.lastname}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not current_user.check_password(old_password):
        return jsonify({'error': 'Old password incorrect'}), 400
    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'}), 200
