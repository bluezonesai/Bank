from flask import Blueprint, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
import random

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Models
class User(Base):
    __tablename__ = \"users\"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    pin: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship
    accounts: Mapped[list[\"Account\"]] = relationship(\"Account\", back_populates=\"owner\")
    
    def to_dict(self):
        return {
            \"id\": self.id,
            \"username\": self.username,
            \"created_at\": self.created_at.isoformat()
        }

class Account(Base):
    __tablename__ = \"accounts\"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default=\"personal\")
    balance: Mapped[float] = mapped_column(Float, default=250000.0)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(\"users.id\"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner: Mapped[\"User\"] = relationship(\"User\", back_populates=\"accounts\")
    sent_transactions: Mapped[list[\"Transaction\"]] = relationship(\"Transaction\", foreign_keys=\"Transaction.from_account_id\", back_populates=\"from_account\")
    received_transactions: Mapped[list[\"Transaction\"]] = relationship(\"Transaction\", foreign_keys=\"Transaction.to_account_id\", back_populates=\"to_account\")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account_number:
            self.account_number = self.generate_account_number()
    
    def generate_account_number(self):
        return str(random.randint(1000000000, 9999999999))
    
    def to_dict(self):
        return {
            \"id\": self.id,
            \"account_number\": self.account_number,
            \"account_type\": self.account_type,
            \"balance\": self.balance,
            \"user_id\": self.user_id,
            \"created_at\": self.created_at.isoformat()
        }

class Transaction(Base):
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    transaction_type: Mapped[str] = mapped_column(String(20), default="transfer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_account: Mapped["Account"] = relationship("Account", foreign_keys=[from_account_id], back_populates="sent_transactions")
    to_account: Mapped["Account"] = relationship("Account", foreign_keys=[to_account_id], back_populates="received_transactions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "amount": self.amount,
            "description": self.description,
            "transaction_type": self.transaction_type,
            "created_at": self.created_at.isoformat()
        }

class RecurringPayment(Base):
    __tablename__ = "recurring_payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")  # weekly, monthly, yearly
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    next_payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_account: Mapped["Account"] = relationship("Account", foreign_keys=[from_account_id])
    to_account: Mapped["Account"] = relationship("Account", foreign_keys=[to_account_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "amount": self.amount,
            "description": self.description,
            "frequency": self.frequency,
            "is_active": self.is_active,
            "next_payment_date": self.next_payment_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "from_account_number": self.from_account.account_number,
            "to_account_number": self.to_account.account_number,
            "recipient_username": self.to_account.owner.username
        }

# Blueprint for routes
bank_bp = Blueprint(\"bank\", __name__)

@bank_bp.route(\"/register\", methods=[\"POST\"])
def register():
    data = request.get_json()
    username = data.get(\"username\")
    pin = data.get(\"pin\")
    account_type = data.get(\"account_type\", \"personal\")
    
    if not username or not pin:
        return jsonify({\"error\": \"Username and PIN are required\"}), 400
    
    if len(pin) != 4 or not pin.isdigit():
        return jsonify({\"error\": \"PIN must be exactly 4 digits\"}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({\"error\": \"Username already exists\"}), 400
    
    # Create new user
    user = User(username=username, pin=pin)
    db.session.add(user)
    db.session.flush()  # Get the user ID
    
    # Create account for the user
    account = Account(user_id=user.id, account_type=account_type)
    db.session.add(account)
    db.session.commit()
    
    return jsonify({
        \"message\": \"User and account created successfully\",
        \"user\": user.to_dict(),
        \"account\": account.to_dict()
    }), 201

@bank_bp.route(\"/login\", methods=[\"POST\"])
def login():
    data = request.get_json()
    username = data.get(\"username\")
    pin = data.get(\"pin\")
    
    if not username or not pin:
        return jsonify({\"error\": \"Username and PIN are required\"}), 400
    
    user = User.query.filter_by(username=username, pin=pin).first()
    if not user:
        return jsonify({\"error\": \"Invalid username or PIN\"}), 401
    
    # Store user in session
    session[\"user_id\"] = user.id
    
    # Get user\'s accounts
    accounts = Account.query.filter_by(user_id=user.id).all()
    
    return jsonify({
        \"message\": \"Login successful\",
        \"user\": user.to_dict(),
        \"accounts\": [account.to_dict() for account in accounts]
    }), 200

@bank_bp.route(\"/logout\", methods=[\"POST\"])
def logout():
    session.pop(\"user_id\", None)
    return jsonify({\"message\": \"Logged out successfully\"}), 200

@bank_bp.route(\"/accounts\", methods=[\"GET\"])
def get_accounts():
    if \"user_id\" not in session:
        return jsonify({\"error\": \"Not logged in\"}), 401
    
    accounts = Account.query.filter_by(user_id=session[\"user_id\"]).all()
    return jsonify([account.to_dict() for account in accounts]), 200

@bank_bp.route(\"/accounts/<int:account_id>/transactions\", methods=[\"GET\"])
def get_transactions(account_id):
    if \"user_id\" not in session:
        return jsonify({\"error\": \"Not logged in\"}), 401
    
    # Verify account belongs to user
    account = Account.query.filter_by(id=account_id, user_id=session[\"user_id\"]).first()
    if not account:
        return jsonify({\"error\": \"Account not found\"}), 404
    
    # Get all transactions for this account
    transactions = Transaction.query.filter(
        (Transaction.from_account_id == account_id) | 
        (Transaction.to_account_id == account_id)
    ).order_by(Transaction.created_at.desc()).all()
    
    return jsonify([transaction.to_dict() for transaction in transactions]), 200

@bank_bp.route(\"/transfer\", methods=[\"POST\"])
def transfer_money():
    if \"user_id\" not in session:
        return jsonify({\"error\": \"Not logged in\"}), 401
    
    data = request.get_json()
    from_account_number = data.get(\"from_account_number\")
    to_account_number = data.get(\"to_account_number\")
    amount = data.get(\"amount\")
    description = data.get(\"description\", \"\")
    
    if not from_account_number or not to_account_number or not amount:
        return jsonify({\"error\": \"From account, to account, and amount are required\"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({\"error\": \"Amount must be positive\"}), 400
    except ValueError:
        return jsonify({\"error\": \"Invalid amount\"}), 400
    
    # Get accounts
    from_account = Account.query.filter_by(account_number=from_account_number, user_id=session[\"user_id\"]).first()
    to_account = Account.query.filter_by(account_number=to_account_number).first()
    
    if not from_account:
        return jsonify({\"error\": \"Source account not found or not owned by you\"}), 404
    
    if not to_account:
        return jsonify({\"error\": \"Destination account not found\"}), 404
    
    if from_account.balance < amount:
        return jsonify({\"error\": \"Insufficient funds\"}), 400
    
    # Perform transfer
    from_account.balance -= amount
    to_account.balance += amount
    
    # Create transaction record
    transaction = Transaction(
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=amount,
        description=description,
        transaction_type=\"transfer\"
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        \"message\": \"Transfer successful\",
        \"transaction\": transaction.to_dict(),
        \"new_balance\": from_account.balance
    }), 200

@bank_bp.route(\"/charge\", methods=[\"POST\"])
def charge_customer():
    if \"user_id\" not in session:
        return jsonify({\"error\": \"Not logged in\"}), 401
    
    data = request.get_json()
    business_account_number = data.get(\"business_account_number\")
    customer_username = data.get(\"customer_username\")
    customer_pin = data.get(\"customer_pin\")
    amount = data.get(\"amount\")
    reason = data.get(\"reason\", \"\")
    description = data.get(\"description\", \"\")
    
    if not all([business_account_number, customer_username, customer_pin, amount, reason]):
        return jsonify({\"error\": \"All fields including reason are required\"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({\"error\": \"Amount must be positive\"}), 400
    except ValueError:
        return jsonify({\"error\": \"Invalid amount\"}), 400
    
    # Verify business account belongs to current user
    business_account = Account.query.filter_by(
        account_number=business_account_number, 
        user_id=session[\"user_id\"],
        account_type=\"business\"
    ).first()
    
    if not business_account:
        return jsonify({\"error\": \"Business account not found or not owned by you\"}), 404
    
    # Verify customer credentials
    customer = User.query.filter_by(username=customer_username, pin=customer_pin).first()
    if not customer:
        return jsonify({\"error\": \"Invalid customer credentials\"}), 401
    
    # Get customer\'s account (assuming first account)
    customer_account = Account.query.filter_by(user_id=customer.id).first()
    if not customer_account:
        return jsonify({\"error\": \"Customer account not found\"}), 404
    
    if customer_account.balance < amount:
        return jsonify({\"error\": \"Customer has insufficient funds\"}), 400
    
    # Perform charge
    customer_account.balance -= amount
    business_account.balance += amount
    
    # Create transaction record with reason in description
    full_description = f\"INVOICE: {reason}\"
    if description:
        full_description += f\" - {description}\"
    
    transaction = Transaction(
        from_account_id=customer_account.id,
        to_account_id=business_account.id,
        amount=amount,
        description=full_description,
        transaction_type=\"charge\"
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        \"message\": \"Charge successful\",
        \"transaction\": transaction.to_dict(),
        \"business_new_balance\": business_account.balance,
        \"invoice\": {
            \"reason\": reason,
            \"amount\": amount,
            \"customer\": customer_username,
            \"business_account\": business_account_number
        }
    }), 200

@bank_bp.route(\"/search_account\", methods=[\"POST\"])
def search_account():
    if \"user_id\" not in session:
        return jsonify({\"error\": \"Not logged in\"}), 401
    
    data = request.get_json()
    account_number = data.get(\"account_number\")
    
    if not account_number:
        return jsonify({\"error\": \"Account number is required\"}), 400
    
    account = Account.query.filter_by(account_number=account_number).first()
    if not account:
        return jsonify({\"error\": \"Account not found\"}), 404
    
    # Return limited info for privacy
    return jsonify({
        \"account_number\": account.account_number,
        \"account_type\": account.account_type,
        \"owner_username\": account.owner.username
    }), 200


@bank_bp.route("/recurring_payments", methods=["POST"])
def create_recurring_payment():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    business_account_number = data.get("business_account_number")
    recipient_account_number = data.get("recipient_account_number")
    amount = data.get("amount")
    description = data.get("description", "Salary Payment")
    frequency = data.get("frequency", "monthly")
    
    if not all([business_account_number, recipient_account_number, amount]):
        return jsonify({"error": "Business account, recipient account, and amount are required"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400
    
    if frequency not in ["weekly", "monthly", "yearly"]:
        return jsonify({"error": "Frequency must be weekly, monthly, or yearly"}), 400
    
    # Verify business account belongs to current user
    business_account = Account.query.filter_by(
        account_number=business_account_number, 
        user_id=session["user_id"],
        account_type="business"
    ).first()
    
    if not business_account:
        return jsonify({"error": "Business account not found or not owned by you"}), 404
    
    # Verify recipient account exists
    recipient_account = Account.query.filter_by(account_number=recipient_account_number).first()
    if not recipient_account:
        return jsonify({"error": "Recipient account not found"}), 404
    
    # Calculate next payment date
    from datetime import timedelta
    next_payment = datetime.utcnow()
    if frequency == "weekly":
        next_payment += timedelta(weeks=1)
    elif frequency == "monthly":
        next_payment += timedelta(days=30)
    elif frequency == "yearly":
        next_payment += timedelta(days=365)
    
    # Create recurring payment
    recurring_payment = RecurringPayment(
        from_account_id=business_account.id,
        to_account_id=recipient_account.id,
        amount=amount,
        description=description,
        frequency=frequency,
        next_payment_date=next_payment
    )
    
    db.session.add(recurring_payment)
    db.session.commit()
    
    return jsonify({
        "message": "Recurring payment created successfully",
        "recurring_payment": recurring_payment.to_dict()
    }), 201

@bank_bp.route("/recurring_payments", methods=["GET"])
def get_recurring_payments():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Get all business accounts for the user
    business_accounts = Account.query.filter_by(
        user_id=session["user_id"],
        account_type="business"
    ).all()
    
    if not business_accounts:
        return jsonify([]), 200
    
    business_account_ids = [account.id for account in business_accounts]
    
    # Get all recurring payments for user's business accounts
    recurring_payments = RecurringPayment.query.filter(
        RecurringPayment.from_account_id.in_(business_account_ids)
    ).all()
    
    return jsonify([payment.to_dict() for payment in recurring_payments]), 200

@bank_bp.route("/recurring_payments/<int:payment_id>", methods=["DELETE"])
def cancel_recurring_payment(payment_id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Find the recurring payment
    recurring_payment = RecurringPayment.query.get(payment_id)
    if not recurring_payment:
        return jsonify({"error": "Recurring payment not found"}), 404
    
    # Verify the payment belongs to user's business account
    business_account = Account.query.filter_by(
        id=recurring_payment.from_account_id,
        user_id=session["user_id"],
        account_type="business"
    ).first()
    
    if not business_account:
        return jsonify({"error": "Unauthorized to cancel this payment"}), 403
    
    # Mark as inactive instead of deleting
    recurring_payment.is_active = False
    db.session.commit()
    
    return jsonify({"message": "Recurring payment cancelled successfully"}), 200

@bank_bp.route("/process_recurring_payments", methods=["POST"])
def process_recurring_payments():
    """Process all due recurring payments - this would normally be called by a scheduler"""
    current_time = datetime.utcnow()
    
    # Find all active recurring payments that are due
    due_payments = RecurringPayment.query.filter(
        RecurringPayment.is_active == True,
        RecurringPayment.next_payment_date <= current_time
    ).all()
    
    processed_count = 0
    failed_count = 0
    
    for payment in due_payments:
        try:
            # Check if business account has sufficient funds
            if payment.from_account.balance >= payment.amount:
                # Process the payment
                payment.from_account.balance -= payment.amount
                payment.to_account.balance += payment.amount
                
                # Create transaction record
                transaction = Transaction(
                    from_account_id=payment.from_account_id,
                    to_account_id=payment.to_account_id,
                    amount=payment.amount,
                    description=f"SALARY: {payment.description}",
                    transaction_type="salary"
                )
                
                db.session.add(transaction)
                
                # Calculate next payment date
                from datetime import timedelta
                if payment.frequency == "weekly":
                    payment.next_payment_date += timedelta(weeks=1)
                elif payment.frequency == "monthly":
                    payment.next_payment_date += timedelta(days=30)
                elif payment.frequency == "yearly":
                    payment.next_payment_date += timedelta(days=365)
                
                processed_count += 1
            else:
                # Insufficient funds - could log this or notify
                failed_count += 1
                
        except Exception as e:
            failed_count += 1
            continue
    
    db.session.commit()
    
    return jsonify({
        "message": f"Processed {processed_count} payments, {failed_count} failed",
        "processed": processed_count,
        "failed": failed_count
    }), 200

