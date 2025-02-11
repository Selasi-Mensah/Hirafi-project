from flask import Blueprint, request, jsonify
from __init__ import db
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


@booking_bp.route('/book_artisan', methods=['POST', 'PUT', 'OPTIONS'],
                  strict_slashes=False)
@jwt_required()
def book_artisan():
    """ Book an artisan
    POST request: Create a booking
    PUT request: Update a booking status

    POST /booking/book_artisan
    PUT /booking/book_artisan
    to_book fields:
        - client_email
        - artisan_email
        - title
        - details
        - completion_date
    }
    Return:
        - Success: JSON with message
            - JSON body:
                - message
        - Error:
            - 401 if user is not authenticated
            - 403 if user is not a client or artisan
            - 404 if client or artisan not found
            - 400 if an error occurred during booking creation
            - 400 if an error occurred during booking update
    """
    
    # check OPTIONS method
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request"}), 200

    # check if user is authenticated
    user_id = get_jwt_identity()
    current_user = User.query.filter_by(id=user_id).first()
    if not current_user:
        return jsonify({"error": "User not authenticated"}), 401

    # handle PUT request
    if request.method == 'PUT':
        if current_user.role != 'Artisan':
            return jsonify({"error": "User is not an artisan"}), 403
        try:
            data = request.get_json()
            booking_id = data.get('booking_id')
            booking = Booking.query.filter_by(id=booking_id).first()
            if not booking:
                return jsonify({"error": "Booking not found"}), 404
            booking.status = data.get('action')
            db.session.commit()
            return jsonify({"message": "Booking updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": f"Invalid request: {str(e)}"}), 400

    # check if user is not a client
    if current_user.role != 'Client':
        return jsonify({"error": "User is not a client"}), 403

    # in postman body must be raw json
    # handle POST request
    try:
        data = request.get_json()
        client_email = data.get('client_email').lower()
        artisan_email = data.get('artisan_email').lower()
        title = data.get('title', '')
        details = data.get('details', '')
        completion_date = data.get('completion_date', '')

        # Validating client and artisan existence
        client = Client.query.filter_by(email=client_email).first()
        artisan = Artisan.query.filter_by(email=artisan_email).first()
        # Convert completion date to datetime object
        completion_date = datetime.strptime(
            completion_date, '%Y-%m-%dT%H:%M:%S.%fZ')

        # Check if completion date is in the past
        if completion_date < datetime.now():
            return jsonify(
                {"error": "Completion date cannot be in the past"}), 400

        # Check if client and artisan exist
        if not client or not artisan:
            return jsonify({"error": "Client or Artisan not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400

    # Creat booking
    try:
        booking = Booking(
            client_id=client.id,
            artisan_id=artisan.id,
            title=title,
            status="Pending",
            request_date=datetime.now(),
            completion_date=completion_date,
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

    You have received a new booking with title {booking.title}.
    You can contact the client {client.name} at {client.phone_number},
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
    """ This route returns all bookings for the current user 
    GET /bookings
        Return:
        - Success: JSON with list of all bookings
            - JSON body:
                - bookings: list of bookings
                - total_pages: total number of pages
                - current_page: current page number
        - Error:
            - 401 if user is not authenticated
            - 400 if an error occurred during pagination
    """
    # check OPTIONS method
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight request"}), 200
    # check if user is authenticated
    user_id = get_jwt_identity()
    current_user = User.query.filter_by(id=user_id).first()
    if not current_user:
        return jsonify({"error": "User not authenticated"}), 401
    # get the bookings
    if current_user.role == 'Artisan':
        bookings = current_user.artisan.bookings
    else:
        bookings = current_user.client.bookings
    # return JSON list of bookings or message if no bookings found
    if not bookings:
        return jsonify({
            'bookings': [],
            'total_pages': 0,
            'current_page': 1
        }), 200

    try:
        # Get query parameters for pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Calculate start and end indices
        start = (page - 1) * per_page
        end = start + per_page

        # Paginate the data
        data = [booking.to_dict() for booking in bookings]
        sorted_bookings = sorted(
            data, key=lambda x: x['request_date'], reverse=True)
        paginated_data = sorted_bookings[start:end]
        total_pages = (len(data) + per_page - 1) // per_page

        return jsonify({
            'bookings': paginated_data,
            'total_pages': total_pages,
            'current_page': page
            }), 200
    except Exception as e:
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400
