"""Reports API endpoints for generating chart data."""
from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, extract
from backend.models import db, Transaction, Category

reports_bp = Blueprint('reports', __name__)


def parse_date_range(request):
    """Parse start and end dates from request parameters."""
    start_date_str = request.args.get('start')
    end_date_str = request.args.get('end')
    
    # Default to last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, None, 'Invalid start date format. Use YYYY-MM-DD'
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, None, 'Invalid end date format. Use YYYY-MM-DD'
    
    return start_date, end_date, None


@reports_bp.route('/spending-by-category', methods=['GET'])
def spending_by_category():
    """Get spending breakdown by category for pie/donut charts."""
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    transaction_type = request.args.get('type', 'expense')
    
    # Query for spending by category - exclude deleted transactions
    if transaction_type == 'income':
        amount_filter = Transaction.amount > 0
    else:
        amount_filter = Transaction.amount < 0
    
    results = db.session.query(
        Category.id,
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.deleted_at.is_(None),  # Exclude deleted
        amount_filter
    ).group_by(
        Category.id
    ).all()
    
    # Also get uncategorized transactions (exclude deleted)
    uncategorized = db.session.query(
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.category_id.is_(None),
        Transaction.deleted_at.is_(None),  # Exclude deleted
        amount_filter
    ).scalar() or 0
    
    data = []
    for cat_id, cat_name, cat_color, total in results:
        data.append({
            'category_id': cat_id,
            'category': cat_name,
            'color': cat_color or '#6c757d',
            'amount': round(abs(total), 2)
        })
    
    if uncategorized:
        data.append({
            'category_id': None,
            'category': 'Uncategorized',
            'color': '#6c757d',
            'amount': round(abs(uncategorized), 2)
        })
    
    # Sort by amount descending
    data.sort(key=lambda x: x['amount'], reverse=True)
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'type': transaction_type,
        'data': data,
        'total': round(sum(d['amount'] for d in data), 2)
    }), 200


@reports_bp.route('/spending-over-time', methods=['GET'])
def spending_over_time():
    """Get spending over time for line/bar charts.
    
    Query parameters:
    - start: Start date (YYYY-MM-DD)
    - end: End date (YYYY-MM-DD)
    - group_by: 'day', 'week', 'month' (default: day)
    - category_id: Optional category filter
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    group_by = request.args.get('group_by', 'day')
    category_id = request.args.get('category_id')
    
    # Base query
    query = db.session.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    )
    
    if category_id:
        query = query.filter(Transaction.category_id == int(category_id))
    
    transactions = query.all()
    
    # Group data
    income_data = {}
    expense_data = {}
    
    for txn in transactions:
        if group_by == 'day':
            key = txn.date.isoformat()
        elif group_by == 'week':
            # Start of week (Monday)
            week_start = txn.date - timedelta(days=txn.date.weekday())
            key = week_start.isoformat()
        else:  # month
            key = txn.date.strftime('%Y-%m')
        
        if txn.amount >= 0:
            income_data[key] = income_data.get(key, 0) + txn.amount
        else:
            expense_data[key] = expense_data.get(key, 0) + abs(txn.amount)
    
    # Create complete date range
    labels = []
    income_values = []
    expense_values = []
    net_values = []
    
    current = start_date
    while current <= end_date:
        if group_by == 'day':
            key = current.isoformat()
            labels.append(current.strftime('%b %d'))
            current += timedelta(days=1)
        elif group_by == 'week':
            week_start = current - timedelta(days=current.weekday())
            key = week_start.isoformat()
            labels.append(f"Week of {week_start.strftime('%b %d')}")
            current += timedelta(weeks=1)
        else:  # month
            key = current.strftime('%Y-%m')
            labels.append(current.strftime('%b %Y'))
            current = (current.replace(day=1) + relativedelta(months=1))
        
        inc = round(income_data.get(key, 0), 2)
        exp = round(expense_data.get(key, 0), 2)
        income_values.append(inc)
        expense_values.append(exp)
        net_values.append(round(inc - exp, 2))
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'group_by': group_by,
        'labels': labels,
        'datasets': {
            'income': income_values,
            'expense': expense_values,
            'net': net_values
        }
    }), 200


@reports_bp.route('/income-vs-expense', methods=['GET'])
def income_vs_expense():
    """Get income vs expense comparison for bar charts.
    
    Query parameters:
    - start: Start date (YYYY-MM-DD)
    - end: End date (YYYY-MM-DD)
    - group_by: 'week', 'month', 'year' (default: month)
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    group_by = request.args.get('group_by', 'month')
    
    transactions = Transaction.query.filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    data = {}
    for txn in transactions:
        if group_by == 'week':
            week_start = txn.date - timedelta(days=txn.date.weekday())
            key = week_start.isoformat()
            label = f"Week of {week_start.strftime('%b %d')}"
        elif group_by == 'year':
            key = str(txn.date.year)
            label = str(txn.date.year)
        else:  # month
            key = txn.date.strftime('%Y-%m')
            label = txn.date.strftime('%b %Y')
        
        if key not in data:
            data[key] = {'label': label, 'income': 0, 'expense': 0}
        
        if txn.amount >= 0:
            data[key]['income'] += txn.amount
        else:
            data[key]['expense'] += abs(txn.amount)
    
    # Sort by date
    sorted_keys = sorted(data.keys())
    
    result = []
    for key in sorted_keys:
        d = data[key]
        result.append({
            'period': key,
            'label': d['label'],
            'income': round(d['income'], 2),
            'expense': round(d['expense'], 2),
            'net': round(d['income'] - d['expense'], 2)
        })
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'group_by': group_by,
        'data': result
    }), 200


@reports_bp.route('/category-trend', methods=['GET'])
def category_trend():
    """Get spending trend for a specific category over time (stacked area chart data).
    
    Query parameters:
    - start: Start date (YYYY-MM-DD)
    - end: End date (YYYY-MM-DD)
    - group_by: 'day', 'week', 'month' (default: week)
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    group_by = request.args.get('group_by', 'week')
    
    # Get all categories with transactions in this period
    categories = db.session.query(
        Category.id,
        Category.name,
        Category.color
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0  # Expenses only
    ).distinct().all()
    
    # Get all transactions
    transactions = Transaction.query.filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0
    ).all()
    
    # Organize data by period and category
    period_data = {}
    for txn in transactions:
        if group_by == 'day':
            key = txn.date.isoformat()
        elif group_by == 'week':
            week_start = txn.date - timedelta(days=txn.date.weekday())
            key = week_start.isoformat()
        else:  # month
            key = txn.date.strftime('%Y-%m')
        
        if key not in period_data:
            period_data[key] = {}
        
        cat_id = txn.category_id or 'uncategorized'
        period_data[key][cat_id] = period_data[key].get(cat_id, 0) + abs(txn.amount)
    
    # Generate labels and datasets
    labels = []
    current = start_date
    while current <= end_date:
        if group_by == 'day':
            key = current.isoformat()
            labels.append({'key': key, 'label': current.strftime('%b %d')})
            current += timedelta(days=1)
        elif group_by == 'week':
            week_start = current - timedelta(days=current.weekday())
            key = week_start.isoformat()
            labels.append({'key': key, 'label': f"Week of {week_start.strftime('%b %d')}"})
            current += timedelta(weeks=1)
        else:  # month
            key = current.strftime('%Y-%m')
            labels.append({'key': key, 'label': current.strftime('%b %Y')})
            current = (current.replace(day=1) + relativedelta(months=1))
    
    datasets = []
    for cat_id, cat_name, cat_color in categories:
        values = []
        for label_info in labels:
            amount = period_data.get(label_info['key'], {}).get(cat_id, 0)
            values.append(round(amount, 2))
        
        datasets.append({
            'category_id': cat_id,
            'label': cat_name,
            'color': cat_color or '#6c757d',
            'data': values
        })
    
    # Add uncategorized if present
    uncategorized_values = []
    has_uncategorized = False
    for label_info in labels:
        amount = period_data.get(label_info['key'], {}).get('uncategorized', 0)
        uncategorized_values.append(round(amount, 2))
        if amount > 0:
            has_uncategorized = True
    
    if has_uncategorized:
        datasets.append({
            'category_id': None,
            'label': 'Uncategorized',
            'color': '#6c757d',
            'data': uncategorized_values
        })
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'group_by': group_by,
        'labels': [l['label'] for l in labels],
        'datasets': datasets
    }), 200


@reports_bp.route('/spending-histogram', methods=['GET'])
def spending_histogram():
    """Get transaction amount distribution for histogram/bar chart.
    
    Query parameters:
    - start: Start date (YYYY-MM-DD)
    - end: End date (YYYY-MM-DD)
    - bins: Number of bins (default: 10)
    - type: 'expense' or 'income' (default: expense)
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    bins = request.args.get('bins', 10, type=int)
    transaction_type = request.args.get('type', 'expense')
    
    # Get transactions
    if transaction_type == 'income':
        amount_filter = Transaction.amount > 0
    else:
        amount_filter = Transaction.amount < 0
    
    transactions = Transaction.query.filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        amount_filter
    ).all()
    
    if not transactions:
        return jsonify({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'type': transaction_type,
            'labels': [],
            'data': [],
            'count': 0
        }), 200
    
    # Get amounts (absolute values)
    amounts = [abs(t.amount) for t in transactions]
    min_amount = min(amounts)
    max_amount = max(amounts)
    
    # Create bins
    if max_amount == min_amount:
        bin_edges = [min_amount, max_amount + 1]
        bin_counts = [len(amounts)]
    else:
        bin_width = (max_amount - min_amount) / bins
        bin_edges = [min_amount + i * bin_width for i in range(bins + 1)]
        bin_counts = [0] * bins
        
        for amount in amounts:
            for i in range(bins):
                if bin_edges[i] <= amount < bin_edges[i + 1] or (i == bins - 1 and amount == bin_edges[i + 1]):
                    bin_counts[i] += 1
                    break
    
    # Create labels
    labels = []
    for i in range(len(bin_counts)):
        if i < len(bin_edges) - 1:
            labels.append(f"${bin_edges[i]:.0f}-${bin_edges[i+1]:.0f}")
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'type': transaction_type,
        'labels': labels,
        'data': bin_counts,
        'count': len(amounts),
        'min': round(min_amount, 2),
        'max': round(max_amount, 2),
        'average': round(sum(amounts) / len(amounts), 2)
    }), 200


@reports_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get overall financial summary.
    
    Query parameters:
    - start: Start date (YYYY-MM-DD)
    - end: End date (YYYY-MM-DD)
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return jsonify({'error': error}), 400
    
    transactions = Transaction.query.filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expense = sum(abs(t.amount) for t in transactions if t.amount < 0)
    net = total_income - total_expense
    
    # Count by category
    category_counts = {}
    for t in transactions:
        cat_name = t.category.name if t.category else 'Uncategorized'
        if cat_name not in category_counts:
            category_counts[cat_name] = {'count': 0, 'total': 0}
        category_counts[cat_name]['count'] += 1
        category_counts[cat_name]['total'] += t.amount
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_income': round(total_income, 2),
        'total_expense': round(total_expense, 2),
        'net': round(net, 2),
        'transaction_count': len(transactions),
        'average_transaction': round(sum(t.amount for t in transactions) / len(transactions), 2) if transactions else 0,
        'category_breakdown': category_counts
    }), 200
