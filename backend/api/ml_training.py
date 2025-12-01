"""API endpoints for ML model training and management."""
from flask import Blueprint, jsonify, request
from backend.ml_categorizer import train_ml_model, get_ml_categorizer, ml_categorize

ml_bp = Blueprint('ml', __name__)


@ml_bp.route('/train', methods=['POST'])
def train_model():
    """Train or retrain the ML categorization model.
    
    Returns:
        Training metrics and results
    """
    try:
        result = train_ml_model()
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/status', methods=['GET'])
def model_status():
    """Get ML model status and information.
    
    Returns:
        Model information including whether it's trained
    """
    categorizer = get_ml_categorizer()
    
    is_trained = categorizer.classifier is not None
    num_categories = len(categorizer.category_mapping) if categorizer.category_mapping else 0
    
    return jsonify({
        'is_trained': is_trained,
        'num_categories': num_categories,
        'categories': list(categorizer.category_mapping.values()) if is_trained else []
    }), 200


@ml_bp.route('/predict', methods=['POST'])
def predict_category():
    """Predict category for given merchant/description.
    
    Request body:
    {
        "merchant": "Starbucks",
        "description": "Coffee purchase",
        "confidence_threshold": 0.3  // optional
    }
    
    Returns:
        Predicted category and confidence
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    merchant = data.get('merchant')
    description = data.get('description')
    threshold = data.get('confidence_threshold', 0.3)
    
    if not merchant and not description:
        return jsonify({'error': 'Either merchant or description required'}), 400
    
    try:
        category_id, confidence = ml_categorize(merchant, description, threshold)
        
        category_name = None
        if category_id:
            from backend.models import Category
            category = Category.query.get(category_id)
            if category:
                category_name = category.name
        
        return jsonify({
            'category_id': category_id,
            'category_name': category_name,
            'confidence': round(confidence, 4)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500