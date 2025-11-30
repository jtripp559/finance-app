"""Categories API endpoints."""
from flask import Blueprint, request, jsonify
from backend.models import db, Category

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('', methods=['GET'])
def list_categories():
    """List all categories.
    
    Query parameters:
    - flat: If 'true', return flat list; otherwise return hierarchical structure
    - parent_id: Filter by parent category ID
    """
    flat = request.args.get('flat', 'false').lower() == 'true'
    parent_id = request.args.get('parent_id')
    
    if parent_id:
        categories = Category.query.filter_by(parent_id=int(parent_id)).all()
        return jsonify([c.to_dict() for c in categories]), 200
    
    if flat:
        categories = Category.query.all()
        return jsonify([c.to_dict() for c in categories]), 200
    
    # Return hierarchical structure
    root_categories = Category.query.filter_by(parent_id=None).all()
    return jsonify([c.to_dict(include_children=True) for c in root_categories]), 200


@categories_bp.route('/hierarchy', methods=['GET'])
def get_category_hierarchy():
    """Get full category hierarchy with nested children."""
    root_categories = Category.query.filter_by(parent_id=None).all()
    
    def build_tree(category):
        result = category.to_dict()
        result['children'] = [build_tree(child) for child in category.children]
        return result
    
    return jsonify([build_tree(c) for c in root_categories]), 200


@categories_bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get a single category by ID."""
    category = Category.query.get_or_404(category_id)
    return jsonify(category.to_dict(include_children=True)), 200


@categories_bp.route('', methods=['POST'])
def create_category():
    """Create a new category.
    
    Request body:
    {
        "name": "string",
        "parent_id": int (optional),
        "icon": "string" (optional),
        "color": "string" (optional)
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    # Check for duplicate name under same parent
    existing = Category.query.filter_by(
        name=data['name'],
        parent_id=data.get('parent_id')
    ).first()
    
    if existing:
        return jsonify({'error': 'Category with this name already exists'}), 409
    
    category = Category(
        name=data['name'],
        parent_id=data.get('parent_id'),
        icon=data.get('icon'),
        color=data.get('color')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Update an existing category.
    
    Request body (all fields optional):
    {
        "name": "string",
        "parent_id": int,
        "icon": "string",
        "color": "string"
    }
    """
    category = Category.query.get_or_404(category_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' in data:
        # Check for duplicate
        existing = Category.query.filter_by(
            name=data['name'],
            parent_id=data.get('parent_id', category.parent_id)
        ).first()
        if existing and existing.id != category_id:
            return jsonify({'error': 'Category with this name already exists'}), 409
        category.name = data['name']
    
    if 'parent_id' in data:
        # Prevent setting self as parent
        if data['parent_id'] == category_id:
            return jsonify({'error': 'Category cannot be its own parent'}), 400
        category.parent_id = data['parent_id']
    
    if 'icon' in data:
        category.icon = data['icon']
    
    if 'color' in data:
        category.color = data['color']
    
    db.session.commit()
    
    return jsonify(category.to_dict()), 200


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete a category.
    
    Note: Transactions with this category will have their category_id set to null.
    Child categories will also be deleted.
    """
    category = Category.query.get_or_404(category_id)
    
    # Recursively delete children
    def delete_children(cat):
        for child in cat.children:
            delete_children(child)
            db.session.delete(child)
    
    delete_children(category)
    
    # Set category_id to null for associated transactions
    from backend.models import Transaction
    Transaction.query.filter_by(category_id=category_id).update({'category_id': None})
    
    db.session.delete(category)
    db.session.commit()
    
    return jsonify({'message': 'Category deleted'}), 200


@categories_bp.route('/<int:category_id>/children', methods=['GET'])
def get_category_children(category_id):
    """Get all children of a category."""
    category = Category.query.get_or_404(category_id)
    return jsonify([c.to_dict() for c in category.children]), 200
