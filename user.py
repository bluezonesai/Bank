# This file is kept for compatibility but all User model functionality
# has been moved to bank.py for the flat structure
# If you need user-specific routes, you can add them here

from flask import Blueprint
from bank import User, db

user_bp = Blueprint("user", __name__)

# Add any user-specific routes here if needed

