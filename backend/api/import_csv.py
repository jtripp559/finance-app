"""CSV Import API endpoint."""
import os
import csv
import io
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from backend.models import db, Transaction
from backend.categorizer import categorize_transaction

import_csv_bp = Blueprint('import_csv', __name__)


def detect_column_type(column_name, sample_values):
    """Detect the probable type of a column based on name and sample values."""
    name_lower = column_name.lower()
    
    # Date detection
    date_keywords = ['date', 'day', 'time', 'posted', 'transaction_date', 'trans_date']
    if any(kw in name_lower for kw in date_keywords):
        return 'date'
    
    # Amount detection
    amount_keywords = ['amount', 'amt', 'value', 'price', 'total', 'debit', 'credit', 'sum']
    if any(kw in name_lower for kw in amount_keywords):
        return 'amount'
    
    # Description detection
    desc_keywords = ['description', 'desc', 'memo', 'narrative', 'details', 'merchant', 'payee', 'name']
    if any(kw in name_lower for kw in desc_keywords):
        return 'description'
    
    # Account detection
    account_keywords = ['account', 'acct', 'card', 'source', 'bank', 'wallet']
    if any(kw in name_lower for kw in account_keywords):
        return 'account'
    
    # Category detection
    cat_keywords = ['category', 'cat', 'type', 'classification']
    if any(kw in name_lower for kw in cat_keywords):
        return 'category'
    
    # Try to detect from sample values
    if sample_values:
        non_empty = [v for v in sample_values if v and str(v).strip()]
        if non_empty:
            # Check if values look like dates
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%Y/%m/%d']
            date_count = 0
            for val in non_empty[:5]:
                for fmt in date_formats:
                    try:
                        datetime.strptime(str(val).strip(), fmt)
                        date_count += 1
                        break
                    except ValueError:
                        pass
            if date_count >= len(non_empty[:5]) * 0.8:
                return 'date'
            
            # Check if values look like numbers (amounts)
            num_count = 0
            for val in non_empty[:5]:
                try:
                    # Remove currency symbols and commas
                    clean_val = str(val).replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
                    float(clean_val)
                    num_count += 1
                except ValueError:
                    pass
            if num_count >= len(non_empty[:5]) * 0.8:
                return 'amount'
    
    return 'unknown'


def parse_amount(value):
    """Parse amount value, handling various formats."""
    if not value:
        return 0.0
    
    val_str = str(value).strip()
    
    # Handle parentheses as negative
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
    
    # Remove currency symbols and commas
    val_str = val_str.replace('$', '').replace(',', '').replace(' ', '')
    
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def parse_date(value, date_format=None):
    """Parse date value with format detection."""
    if not value:
        return None
    
    val_str = str(value).strip()
    
    if date_format:
        try:
            return datetime.strptime(val_str, date_format).date()
        except ValueError:
            pass
    
    # Try common formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%Y/%m/%d',
        '%m/%d/%y',
        '%d-%m-%Y',
        '%b %d, %Y',
        '%B %d, %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    
    return None


@import_csv_bp.route('', methods=['POST'])
def import_csv():
    """Import transactions from CSV file.
    
    This endpoint handles two modes:
    1. Preview mode (no mapping provided): Returns column detection and sample data
    2. Import mode (mapping provided): Imports transactions using the provided mapping
    
    Form data:
    - file: CSV file (required)
    - mapping: JSON string with column mapping (optional, for import mode)
      {
        "date": "Date Column Name",
        "amount": "Amount Column Name",
        "description": "Description Column Name",
        "date_format": "%Y-%m-%d" (optional)
      }
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        # Read file content
        content = file.read().decode('utf-8-sig')  # Handle BOM
        reader = csv.DictReader(io.StringIO(content))
        
        # Get headers
        headers = reader.fieldnames
        if not headers:
            return jsonify({'error': 'CSV file has no headers'}), 400
        
        # Read all rows
        rows = list(reader)
        if not rows:
            return jsonify({'error': 'CSV file has no data rows'}), 400
        
        # Check if mapping is provided (import mode)
        mapping_str = request.form.get('mapping')
        
        if mapping_str:
            # Import mode
            import json
            try:
                mapping = json.loads(mapping_str)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid mapping JSON'}), 400
            
            # Validate mapping
            required_fields = ['date', 'amount', 'description']
            for field in required_fields:
                if field not in mapping or mapping[field] not in headers:
                    return jsonify({'error': f'Missing or invalid mapping for {field}'}), 400
            
            # Import transactions
            created = []
            errors = []
            date_format = mapping.get('date_format')
            
            for i, row in enumerate(rows):
                try:
                    date_val = parse_date(row[mapping['date']], date_format)
                    if not date_val:
                        errors.append({'row': i + 1, 'error': 'Invalid date'})
                        continue
                    
                    amount = parse_amount(row[mapping['amount']])
                    description = row[mapping['description']].strip() if row[mapping['description']] else ''
                    
                    if not description:
                        errors.append({'row': i + 1, 'error': 'Empty description'})
                        continue
                    
                    # Auto-categorize
                    category_id = categorize_transaction(description)
                    
                    transaction = Transaction(
                        date=date_val,
                        amount=amount,
                        description=description,
                        account_name=row.get(mapping.get('account', ''), '').strip() if mapping.get('account') else None,
                        category_id=category_id
                    )
                    db.session.add(transaction)
                    created.append(transaction)
                except Exception as e:
                    errors.append({'row': i + 1, 'error': str(e)})
            
            if created:
                db.session.commit()
            
            return jsonify({
                'success': True,
                'imported_count': len(created),
                'error_count': len(errors),
                'errors': errors[:10]  # Return first 10 errors
            }), 201
        
        else:
            # Preview mode - detect columns and return sample data
            sample_rows = rows[:10]
            
            # Collect sample values for each column
            column_samples = {}
            for header in headers:
                column_samples[header] = [row.get(header, '') for row in sample_rows]
            
            # Detect column types
            column_suggestions = {}
            for header in headers:
                detected_type = detect_column_type(header, column_samples[header])
                column_suggestions[header] = detected_type
            
            # Auto-suggest mapping
            suggested_mapping = {}
            for header, col_type in column_suggestions.items():
                if col_type != 'unknown' and col_type not in suggested_mapping.values():
                    suggested_mapping[col_type] = header
            
            return jsonify({
                'success': True,
                'mode': 'preview',
                'total_rows': len(rows),
                'headers': headers,
                'column_suggestions': column_suggestions,
                'suggested_mapping': suggested_mapping,
                'sample_data': sample_rows,
                'date_formats': [
                    {'value': '%Y-%m-%d', 'label': 'YYYY-MM-DD (e.g., 2025-01-15)'},
                    {'value': '%m/%d/%Y', 'label': 'MM/DD/YYYY (e.g., 01/15/2025)'},
                    {'value': '%d/%m/%Y', 'label': 'DD/MM/YYYY (e.g., 15/01/2025)'},
                    {'value': '%m-%d-%Y', 'label': 'MM-DD-YYYY (e.g., 01-15-2025)'},
                ]
            }), 200
    
    except UnicodeDecodeError:
        return jsonify({'error': 'Could not decode file. Please ensure it is UTF-8 encoded.'}), 400
    except Exception as e:
        # Log the full error for debugging but return generic message to client
        current_app.logger.error(f'CSV import error: {str(e)}')
        return jsonify({'error': 'An error occurred while processing the file. Please check the file format and try again.'}), 500
