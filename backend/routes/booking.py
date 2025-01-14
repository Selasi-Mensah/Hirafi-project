from flask import Blueprint, request, jsonify
from __init__ import db, bcrypt
from models.client import Client
from models.user import User
from models.artisan import Artisan
from models.booking import Booking
from forms.auth import RegistrationForm, LoginForm
from flask_jwt_extended import jwt_required, get_jwt_identity
# I will create this later
from utils.email_service import send_email
from datetime import datetime


# Create the Blueprint
# booking_bp = Blueprint('booking', __name__, url_prefix='/booking')
booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/book_artisan', methods=['POST', 'OPTIONS'],
                  strict_slashes=False)
@jwt_required()
def book_artisan():
    """ Book an artisan """
    # check OPTIONS method
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request"}), 200

    # check if user is authenticated
    user_id = get_jwt_identity()
    current_user = User.query.filter_by(id=user_id).first()
    if not current_user:
        return jsonify({"error": "User not authenticated"}), 403

    # in postman body must be raw json
    data = request.get_json()
    client_email = data.get('client_email')
    artisan_email = data.get('artisan_email')
    details = data.get('details', '')

    # Validating client and artisan existence
    client = Client.query.filter_by(email=client_email).first()
    artisan = Artisan.query.filter_by(email=artisan_email).first()

    if not client or not artisan:
        return jsonify({"error": "Client or Artisan not found"}), 404

    # Creat booking
    try:
        booking = Booking(
            client_id=client.id,
            artisan_id=artisan.id,
            status="Pending",
            request_date=datetime.now(),
            completion_date=datetime.now(),
            details=details,
            created_at=datetime.now(),
        )
    except Exception as e:
        return jsonify({"error": f"Unable to create booking: {str(e)}"}), 500
    db.session.add(booking)
    db.session.commit()

    # Sending notification email to the artisan
    subject = f"HIRAFIC: New Booking from {client.name}"
    body = f"""
    Hello {artisan.name},

    You have received a new booking from {client.name}.
    You can contact the client at {client.phone_number},
    or at this email address {client.email}.

    Booking Details:
    {details}

    Requested Date:
        {booking.request_date.strftime('%Y-%m-%d %H:%M:%S')}

    Expected Completion Date:
        {booking.completion_date.strftime('%Y-%m-%d %H:%M:%S')}

    Please view the booking details in your dashboard.

    Best regards,
    Your HIRAFIC Booking Team
    """
    send_email(artisan.email, subject, body)

    return jsonify(
        {"message": "Booking created and email sent successfully!"}), 201


@booking_bp.route(
        "/bookings",
        methods=['GET', 'OPTIONS'], strict_slashes=False)
@jwt_required()
def bookings():
    """ This route returns all bookings for the current user """
    # check OPTIONS method
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request"}), 200
    # check if user is authenticated
    user_id = get_jwt_identity()
    current_user = User.query.filter_by(id=user_id).first()
    if not current_user:
        return jsonify({"error": "User not authenticated"}), 403
    # get the bookings
    if current_user.role == 'Artisan':
        bookings = current_user.artisan.bookings
    else:
        bookings = current_user.client.bookings
    # return JSON list of bookings
    return jsonify([booking.to_dict() for booking in bookings]), 200
