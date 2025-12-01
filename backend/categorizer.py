"""Transaction categorization engine with rule-based and ML classifier stub."""
import re
from backend.models import db, CategorizationRule, Category


def categorize_transaction(merchant=None, description=None):
    """Categorize a transaction based on merchant and description.
    
    Args:
        merchant: Merchant name (primary for matching)
        description: Transaction description (secondary)
    
    Returns:
        category_id or None if no match found
    """
    # Prioritize merchant for matching, fall back to description
    primary_text = (merchant or '').lower().strip()
    secondary_text = (description or '').lower().strip()
    
    # First, try rule-based categorization on merchant
    if primary_text:
        category_id = rule_based_categorize(primary_text)
        if category_id:
            return category_id
    
    # Then try on description
    if secondary_text:
        category_id = rule_based_categorize(secondary_text)
        if category_id:
            return category_id
    
    # Try combined text
    combined_text = f"{primary_text} {secondary_text}".strip()
    if combined_text:
        category_id = rule_based_categorize(combined_text)
        if category_id:
            return category_id
    
    # Fall back to classifier (stub)
    category_id = classifier_predict(combined_text)
    if category_id:
        return category_id
    
    # Return uncategorized category if exists
    uncategorized = Category.query.filter_by(name='Uncategorized').first()
    return uncategorized.id if uncategorized else None


def rule_based_categorize(text):
    """Apply rule-based categorization.
    
    Args:
        text: Combined transaction text (description + merchant)
    
    Returns:
        category_id or None
    """
    # Get all rules ordered by priority
    rules = CategorizationRule.query.order_by(CategorizationRule.priority.desc()).all()
    
    for rule in rules:
        match = False
        pattern = rule.pattern.lower()
        
        if rule.match_type == 'exact':
            match = pattern == text
        elif rule.match_type == 'contains':
            match = pattern in text
        elif rule.match_type == 'regex':
            try:
                match = bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                continue
        
        if match:
            return rule.category_id
    
    return None


def classifier_predict(text):
    """ML classifier stub for transaction categorization.
    
    This is a placeholder for a trained machine learning model.
    In a production system, this would load a trained model and
    make predictions based on the transaction text.
    
    Args:
        text: Combined transaction text
    
    Returns:
        category_id or None
    
    Integration notes:
    - Load a trained model (e.g., scikit-learn, TensorFlow)
    - Vectorize the text using the same method as training
    - Get prediction probabilities
    - Return category_id if confidence > threshold
    
    Example implementation with scikit-learn:
    
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Load model and vectorizer (cache these)
    model = joblib.load('models/categorizer.pkl')
    vectorizer = joblib.load('models/vectorizer.pkl')
    
    # Vectorize and predict
    X = vectorizer.transform([text])
    probabilities = model.predict_proba(X)[0]
    predicted_idx = probabilities.argmax()
    confidence = probabilities[predicted_idx]
    
    if confidence > 0.7:
        category_mapping = joblib.load('models/category_mapping.pkl')
        return category_mapping[predicted_idx]
    
    return None
    """
    # Stub implementation - returns None
    # Replace with actual ML model prediction
    return None


def train_classifier(transactions):
    """Train the ML classifier on labeled transactions.
    
    This is a stub for the training pipeline.
    
    Args:
        transactions: List of Transaction objects with category_id set
    
    Returns:
        dict with training metrics
    
    Implementation notes:
    - Filter transactions with valid category_id
    - Split into train/test sets
    - Vectorize descriptions (TF-IDF, word embeddings, etc.)
    - Train a classifier (Naive Bayes, SVM, Neural Network)
    - Evaluate and save model
    """
    # Stub implementation
    return {
        'status': 'not_implemented',
        'message': 'ML classifier training is a stub. Implement with your preferred ML framework.'
    }


def add_categorization_rule(pattern, category_id, match_type='contains', priority=0):
    """Add a new categorization rule.
    
    Args:
        pattern: Pattern to match against transaction text
        category_id: Category ID to assign when matched
        match_type: 'contains', 'exact', or 'regex'
        priority: Higher priority rules are checked first
    
    Returns:
        The created CategorizationRule
    """
    # Check if rule already exists
    existing = CategorizationRule.query.filter_by(
        pattern=pattern,
        category_id=category_id
    ).first()
    
    if existing:
        existing.match_type = match_type
        existing.priority = priority
        db.session.commit()
        return existing
    
    rule = CategorizationRule(
        pattern=pattern,
        category_id=category_id,
        match_type=match_type,
        priority=priority
    )
    db.session.add(rule)
    db.session.commit()
    return rule


def delete_categorization_rule(rule_id):
    """Delete a categorization rule.
    
    Args:
        rule_id: ID of the rule to delete
    
    Returns:
        True if deleted, False if not found
    """
    rule = CategorizationRule.query.get(rule_id)
    if rule:
        db.session.delete(rule)
        db.session.commit()
        return True
    return False


def get_categorization_rules():
    """Get all categorization rules.
    
    Returns:
        List of CategorizationRule objects
    """
    return CategorizationRule.query.order_by(CategorizationRule.priority.desc()).all()


def recategorize_transactions(category_id=None):
    """Re-run categorization on existing transactions.
    
    Args:
        category_id: If provided, only recategorize transactions in this category.
                    If None, recategorize all uncategorized transactions.
    
    Returns:
        dict with counts of updated transactions
    """
    from backend.models import Transaction
    
    if category_id:
        transactions = Transaction.query.filter_by(category_id=category_id).all()
    else:
        # Get uncategorized category
        uncategorized = Category.query.filter_by(name='Uncategorized').first()
        if uncategorized:
            transactions = Transaction.query.filter(
                (Transaction.category_id.is_(None)) | 
                (Transaction.category_id == uncategorized.id)
            ).all()
        else:
            transactions = Transaction.query.filter(Transaction.category_id.is_(None)).all()
    
    updated = 0
    for txn in transactions:
        new_category_id = categorize_transaction(txn.merchant, txn.description)
        if new_category_id and new_category_id != txn.category_id:
            txn.category_id = new_category_id
            updated += 1
    
    if updated:
        db.session.commit()
    
    return {
        'total_processed': len(transactions),
        'updated': updated
    }
