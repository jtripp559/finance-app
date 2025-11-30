"""Transactions API endpoints."""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.models import db, Transaction, Category
from backend.categorizer import categorize_transaction

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('', methods=['GET'])
def list_transactions():
    """List all transactions with optional filtering.
    
    Query parameters:
    - start_date: Filter transactions on or after this date (YYYY-MM-DD)
    - end_date: Filter transactions on or before this date (YYYY-MM-DD)
    - category_id: Filter by category ID
    - account_name: Filter by account name
    - min_amount: Filter by minimum amount
    - max_amount: Filter by maximum amount
    - search: Search in description
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    """
    query = Transaction.query
    
    # Date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date >= start)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date <= end)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
    
    # Category filter
    category_id = request.args.get('category_id')
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    # Account name filter
    account_name = request.args.get('account_name')
    if account_name:
        query = query.filter(Transaction.account_name == account_name)
    
    # Amount filters
    min_amount = request.args.get('min_amount')
    max_amount = request.args.get('max_amount')
    
    if min_amount:
        try:
            query = query.filter(Transaction.amount >= float(min_amount))
        except ValueError:
            return jsonify({'error': 'Invalid min_amount'}), 400
    
    if max_amount:
        try:
            query = query.filter(Transaction.amount <= float(max_amount))
        except ValueError:
            return jsonify({'error': 'Invalid max_amount'}), 400
    
    # Search filter
    search = request.args.get('search')
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)  # Max 100 per page
    
    # Order by date descending
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@transactions_bp.route('/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a single transaction by ID."""
    transaction = Transaction.query.get_or_404(transaction_id)
    return jsonify(transaction.to_dict()), 200


@transactions_bp.route('', methods=['POST'])
def create_transaction():
    """Create a new transaction.
    
    Request body:
    {
        "date": "YYYY-MM-DD",
        "amount": float,
        "description": "string",
        "merchant": "string" (optional),
        "account_name": "string" (optional),
        "category_id": int (optional),
        "notes": "string" (optional)
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    if 'date' not in data:
        return jsonify({'error': 'Date is required'}), 400
    if 'amount' not in data:
        return jsonify({'error': 'Amount is required'}), 400
    if 'description' not in data:
        return jsonify({'error': 'Description is required'}), 400
    
    # Parse date
    try:
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Parse amount
    try:
        amount = float(data['amount'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400
    
    # Auto-categorize if no category provided
    category_id = data.get('category_id')
    if not category_id:
        category_id = categorize_transaction(data['description'], data.get('merchant'))
    
    transaction = Transaction(
        date=date,
        amount=amount,
        description=data['description'],
        merchant=data.get('merchant'),
        account_name=data.get('account_name'),
        category_id=category_id,
        notes=data.get('notes')
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify(transaction.to_dict()), 201


@transactions_bp.route('/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update an existing transaction.
    
    Request body (all fields optional):
    {
        "date": "YYYY-MM-DD",
        "amount": float,
        "description": "string",
        "merchant": "string",
        "account_name": "string",
        "category_id": int,
        "notes": "string"
    }
    """
    transaction = Transaction.query.get_or_404(transaction_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'date' in data:
        try:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    if 'amount' in data:
        try:
            transaction.amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400
    
    if 'description' in data:
        transaction.description = data['description']
    
    if 'merchant' in data:
        transaction.merchant = data['merchant']
    
    if 'account_name' in data:
        transaction.account_name = data['account_name']
    
    if 'category_id' in data:
        transaction.category_id = data['category_id']
    
    if 'notes' in data:
        transaction.notes = data['notes']
    
    db.session.commit()
    
    return jsonify(transaction.to_dict()), 200


@transactions_bp.route('/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Transaction deleted'}), 200


@transactions_bp.route('/bulk', methods=['POST'])
def bulk_create_transactions():
    """Create multiple transactions at once.
    
    Request body:
    {
        "transactions": [
            {
                "date": "YYYY-MM-DD",
                "amount": float,
                "description": "string",
                ...
            }
        ]
    }
    """
    data = request.get_json()
    
    if not data or 'transactions' not in data:
        return jsonify({'error': 'No transactions provided'}), 400
    
    created = []
    errors = []
    
    for i, txn_data in enumerate(data['transactions']):
        try:
            # Validate required fields
            if 'date' not in txn_data or 'amount' not in txn_data or 'description' not in txn_data:
                errors.append({'index': i, 'error': 'Missing required fields'})
                continue
            
            date = datetime.strptime(txn_data['date'], '%Y-%m-%d').date()
            amount = float(txn_data['amount'])
            
            # Auto-categorize if no category provided
            category_id = txn_data.get('category_id')
            if not category_id:
                category_id = categorize_transaction(txn_data['description'], txn_data.get('merchant'))
            
            transaction = Transaction(
                date=date,
                amount=amount,
                description=txn_data['description'],
                merchant=txn_data.get('merchant'),
                account_name=txn_data.get('account_name'),
                category_id=category_id,
                notes=txn_data.get('notes')
            )
            db.session.add(transaction)
            created.append(transaction)
        except Exception as e:
            errors.append({'index': i, 'error': str(e)})
    
    if created:
        db.session.commit()
    
    return jsonify({
        'created': [t.to_dict() for t in created],
        'created_count': len(created),
        'errors': errors,
        'error_count': len(errors)
    }), 201 if created else 400


@transactions_bp.route('/accounts', methods=['GET'])
def list_accounts():
    """Get list of unique account names."""
    accounts = db.session.query(Transaction.account_name).filter(
        Transaction.account_name.isnot(None)
    ).distinct().order_by(Transaction.account_name).all()
    
    return jsonify([a[0] for a in accounts if a[0]]), 200
