"""Budgets API endpoints."""
from flask import Blueprint, request, jsonify
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from backend.models import db, Budget, Transaction, Category
from sqlalchemy import func

budgets_bp = Blueprint('budgets', __name__)


def get_period_dates(period, reference_date=None):
    """Get start and end dates for a budget period."""
    if reference_date is None:
        reference_date = date.today()
    
    if period == 'weekly':
        # Start from Monday of current week
        start = reference_date - relativedelta(days=reference_date.weekday())
        end = start + relativedelta(days=6)
    elif period == 'monthly':
        start = reference_date.replace(day=1)
        end = start + relativedelta(months=1, days=-1)
    elif period == 'yearly':
        start = reference_date.replace(month=1, day=1)
        end = reference_date.replace(month=12, day=31)
    else:
        # Default to monthly
        start = reference_date.replace(day=1)
        end = start + relativedelta(months=1, days=-1)
    
    return start, end


@budgets_bp.route('', methods=['GET'])
def list_budgets():
    """List all budgets with spending progress.
    
    Query parameters:
    - period: Filter by period (weekly, monthly, yearly)
    - category_id: Filter by category ID
    - include_spending: If 'true', include current spending amount (default: true)
    """
    query = Budget.query
    
    period = request.args.get('period')
    if period:
        query = query.filter_by(period=period)
    
    category_id = request.args.get('category_id')
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    
    budgets = query.all()
    include_spending = request.args.get('include_spending', 'true').lower() == 'true'
    
    result = []
    for budget in budgets:
        budget_dict = budget.to_dict()
        
        if include_spending:
            start, end = get_period_dates(budget.period)
            
            # Get spending for this category in the period
            spending_query = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.deleted_at.is_(None),  # Exclude deleted transactions
                Transaction.amount < 0  # Only expenses (negative amounts)
            )
            
            if budget.category_id:
                # Include subcategories
                category = Category.query.get(budget.category_id)
                category_ids = [budget.category_id]
                if category:
                    category_ids.extend([c.id for c in category.children])
                spending_query = spending_query.filter(Transaction.category_id.in_(category_ids))
            
            spent = spending_query.scalar() or 0
            spent = abs(spent)  # Convert to positive for comparison
            
            budget_dict['spent'] = round(spent, 2)
            budget_dict['remaining'] = round(budget.amount - spent, 2)
            budget_dict['percent_used'] = round((spent / budget.amount * 100) if budget.amount > 0 else 0, 1)
            budget_dict['period_start'] = start.isoformat()
            budget_dict['period_end'] = end.isoformat()
        
        result.append(budget_dict)
    
    return jsonify(result), 200


@budgets_bp.route('/summary', methods=['GET'])
def get_budget_summary():
    """Get budget summary with spending vs budget comparison.
    
    Query parameters:
    - period: Budget period to summarize (weekly, monthly, yearly). Default: monthly
    - date: Reference date for period calculation (YYYY-MM-DD). Default: today
    """
    period = request.args.get('period', 'monthly')
    reference_date_str = request.args.get('date')
    
    if reference_date_str:
        try:
            reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    else:
        reference_date = date.today()
    
    start, end = get_period_dates(period, reference_date)
    
    # Get all budgets for this period
    budgets = Budget.query.filter_by(period=period).all()
    
    # Calculate total budget and spending
    total_budget = sum(b.amount for b in budgets)
    
    # Get total spending for the period
    total_spending = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.date >= start,
        Transaction.date <= end,
        Transaction.amount < 0
    ).scalar() or 0
    total_spending = abs(total_spending)
    
    # Per-category breakdown
    categories = []
    for budget in budgets:
        category_ids = [budget.category_id] if budget.category_id else []
        
        if budget.category_id:
            category = Category.query.get(budget.category_id)
            if category:
                category_ids.extend([c.id for c in category.children])
        
        if category_ids:
            spent = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.amount < 0,
                Transaction.category_id.in_(category_ids)
            ).scalar() or 0
        else:
            spent = 0
        
        spent = abs(spent)
        
        categories.append({
            'budget_id': budget.id,
            'budget_name': budget.name,
            'category_id': budget.category_id,
            'category_name': budget.category.name if budget.category else None,
            'budgeted': budget.amount,
            'spent': round(spent, 2),
            'remaining': round(budget.amount - spent, 2),
            'percent_used': round((spent / budget.amount * 100) if budget.amount > 0 else 0, 1),
            'status': 'over' if spent > budget.amount else ('warning' if spent > budget.amount * 0.8 else 'good')
        })
    
    return jsonify({
        'period': period,
        'period_start': start.isoformat(),
        'period_end': end.isoformat(),
        'total_budget': round(total_budget, 2),
        'total_spending': round(total_spending, 2),
        'total_remaining': round(total_budget - total_spending, 2),
        'overall_percent_used': round((total_spending / total_budget * 100) if total_budget > 0 else 0, 1),
        'categories': categories
    }), 200


@budgets_bp.route('/<int:budget_id>', methods=['GET'])
def get_budget(budget_id):
    """Get a single budget by ID with spending details."""
    budget = Budget.query.get_or_404(budget_id)
    budget_dict = budget.to_dict()
    
    start, end = get_period_dates(budget.period)
    
    # Get spending for this category
    spending_query = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.date >= start,
        Transaction.date <= end,
        Transaction.amount < 0
    )
    
    if budget.category_id:
        category = Category.query.get(budget.category_id)
        category_ids = [budget.category_id]
        if category:
            category_ids.extend([c.id for c in category.children])
        spending_query = spending_query.filter(Transaction.category_id.in_(category_ids))
    
    spent = abs(spending_query.scalar() or 0)
    
    budget_dict['spent'] = round(spent, 2)
    budget_dict['remaining'] = round(budget.amount - spent, 2)
    budget_dict['percent_used'] = round((spent / budget.amount * 100) if budget.amount > 0 else 0, 1)
    budget_dict['period_start'] = start.isoformat()
    budget_dict['period_end'] = end.isoformat()
    
    return jsonify(budget_dict), 200


@budgets_bp.route('', methods=['POST'])
def create_budget():
    """Create a new budget.
    
    Request body:
    {
        "name": "string",
        "amount": float,
        "period": "monthly" | "weekly" | "yearly",
        "category_id": int (optional),
        "start_date": "YYYY-MM-DD" (optional),
        "end_date": "YYYY-MM-DD" (optional)
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    if 'amount' not in data:
        return jsonify({'error': 'Amount is required'}), 400
    
    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400
    
    period = data.get('period', 'monthly')
    if period not in ['weekly', 'monthly', 'yearly']:
        return jsonify({'error': 'Invalid period. Must be weekly, monthly, or yearly'}), 400
    
    budget = Budget(
        name=data['name'],
        amount=amount,
        period=period,
        category_id=data.get('category_id')
    )
    
    if 'start_date' in data:
        try:
            budget.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400
    
    if 'end_date' in data:
        try:
            budget.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400
    
    db.session.add(budget)
    db.session.commit()
    
    return jsonify(budget.to_dict()), 201


@budgets_bp.route('/<int:budget_id>', methods=['PUT'])
def update_budget(budget_id):
    """Update an existing budget."""
    budget = Budget.query.get_or_404(budget_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' in data:
        budget.name = data['name']
    
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
            budget.amount = amount
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400
    
    if 'period' in data:
        if data['period'] not in ['weekly', 'monthly', 'yearly']:
            return jsonify({'error': 'Invalid period'}), 400
        budget.period = data['period']
    
    if 'category_id' in data:
        budget.category_id = data['category_id']
    
    if 'start_date' in data:
        try:
            budget.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400
    
    if 'end_date' in data:
        try:
            budget.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400
    
    db.session.commit()
    
    return jsonify(budget.to_dict()), 200


@budgets_bp.route('/<int:budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    """Delete a budget."""
    budget = Budget.query.get_or_404(budget_id)
    db.session.delete(budget)
    db.session.commit()
    
    return jsonify({'message': 'Budget deleted'}), 200
