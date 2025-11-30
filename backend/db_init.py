"""Database initialization and seeding script."""
from backend.models import db, User, Category, CategorizationRule
from werkzeug.security import generate_password_hash


def init_db(app):
    """Initialize the database schema."""
    with app.app_context():
        db.create_all()


def seed_categories():
    """Seed default categories."""
    default_categories = [
        {'name': 'Income', 'icon': 'cash-coin', 'color': '#28a745', 'children': [
            {'name': 'Salary', 'icon': 'briefcase', 'color': '#28a745'},
            {'name': 'Investments', 'icon': 'graph-up', 'color': '#28a745'},
            {'name': 'Other Income', 'icon': 'plus-circle', 'color': '#28a745'},
        ]},
        {'name': 'Housing', 'icon': 'house', 'color': '#007bff', 'children': [
            {'name': 'Rent/Mortgage', 'icon': 'building', 'color': '#007bff'},
            {'name': 'Utilities', 'icon': 'lightbulb', 'color': '#007bff'},
            {'name': 'Home Maintenance', 'icon': 'tools', 'color': '#007bff'},
        ]},
        {'name': 'Transportation', 'icon': 'car-front', 'color': '#17a2b8', 'children': [
            {'name': 'Gas', 'icon': 'fuel-pump', 'color': '#17a2b8'},
            {'name': 'Car Payment', 'icon': 'car-front', 'color': '#17a2b8'},
            {'name': 'Public Transit', 'icon': 'bus-front', 'color': '#17a2b8'},
            {'name': 'Parking', 'icon': 'p-circle', 'color': '#17a2b8'},
        ]},
        {'name': 'Food & Dining', 'icon': 'basket', 'color': '#ffc107', 'children': [
            {'name': 'Groceries', 'icon': 'cart', 'color': '#ffc107'},
            {'name': 'Restaurants', 'icon': 'cup-hot', 'color': '#ffc107'},
            {'name': 'Coffee Shops', 'icon': 'cup', 'color': '#ffc107'},
            {'name': 'Fast Food', 'icon': 'basket', 'color': '#ffc107'},
        ]},
        {'name': 'Shopping', 'icon': 'bag', 'color': '#e83e8c', 'children': [
            {'name': 'Clothing', 'icon': 'handbag', 'color': '#e83e8c'},
            {'name': 'Electronics', 'icon': 'laptop', 'color': '#e83e8c'},
            {'name': 'Home Goods', 'icon': 'lamp', 'color': '#e83e8c'},
        ]},
        {'name': 'Entertainment', 'icon': 'film', 'color': '#6f42c1', 'children': [
            {'name': 'Movies', 'icon': 'film', 'color': '#6f42c1'},
            {'name': 'Streaming Services', 'icon': 'tv', 'color': '#6f42c1'},
            {'name': 'Games', 'icon': 'controller', 'color': '#6f42c1'},
            {'name': 'Hobbies', 'icon': 'palette', 'color': '#6f42c1'},
        ]},
        {'name': 'Healthcare', 'icon': 'heart-pulse', 'color': '#dc3545', 'children': [
            {'name': 'Medical', 'icon': 'hospital', 'color': '#dc3545'},
            {'name': 'Pharmacy', 'icon': 'capsule', 'color': '#dc3545'},
            {'name': 'Insurance', 'icon': 'shield-check', 'color': '#dc3545'},
        ]},
        {'name': 'Personal', 'icon': 'person', 'color': '#fd7e14', 'children': [
            {'name': 'Personal Care', 'icon': 'scissors', 'color': '#fd7e14'},
            {'name': 'Education', 'icon': 'book', 'color': '#fd7e14'},
            {'name': 'Subscriptions', 'icon': 'journal', 'color': '#fd7e14'},
        ]},
        {'name': 'Uncategorized', 'icon': 'question-circle', 'color': '#6c757d'},
    ]
    
    def create_category(cat_data, parent_id=None):
        existing = Category.query.filter_by(name=cat_data['name'], parent_id=parent_id).first()
        if not existing:
            category = Category(
                name=cat_data['name'],
                parent_id=parent_id,
                icon=cat_data.get('icon'),
                color=cat_data.get('color')
            )
            db.session.add(category)
            db.session.flush()
            
            for child_data in cat_data.get('children', []):
                create_category(child_data, category.id)
    
    for cat_data in default_categories:
        create_category(cat_data)
    
    db.session.commit()


def seed_categorization_rules():
    """Seed default categorization rules."""
    # Get categories
    groceries = Category.query.filter_by(name='Groceries').first()
    restaurants = Category.query.filter_by(name='Restaurants').first()
    coffee = Category.query.filter_by(name='Coffee Shops').first()
    gas = Category.query.filter_by(name='Gas').first()
    streaming = Category.query.filter_by(name='Streaming Services').first()
    fast_food = Category.query.filter_by(name='Fast Food').first()
    
    rules = []
    
    if groceries:
        rules.extend([
            {'pattern': 'walmart', 'category_id': groceries.id, 'priority': 10},
            {'pattern': 'kroger', 'category_id': groceries.id, 'priority': 10},
            {'pattern': 'safeway', 'category_id': groceries.id, 'priority': 10},
            {'pattern': 'trader joe', 'category_id': groceries.id, 'priority': 10},
            {'pattern': 'whole foods', 'category_id': groceries.id, 'priority': 10},
            {'pattern': 'costco', 'category_id': groceries.id, 'priority': 10},
        ])
    
    if restaurants:
        rules.extend([
            {'pattern': 'restaurant', 'category_id': restaurants.id, 'priority': 5},
            {'pattern': 'grill', 'category_id': restaurants.id, 'priority': 5},
            {'pattern': 'diner', 'category_id': restaurants.id, 'priority': 5},
        ])
    
    if coffee:
        rules.extend([
            {'pattern': 'starbucks', 'category_id': coffee.id, 'priority': 10},
            {'pattern': 'dunkin', 'category_id': coffee.id, 'priority': 10},
            {'pattern': 'coffee', 'category_id': coffee.id, 'priority': 5},
        ])
    
    if gas:
        rules.extend([
            {'pattern': 'shell', 'category_id': gas.id, 'priority': 10},
            {'pattern': 'exxon', 'category_id': gas.id, 'priority': 10},
            {'pattern': 'chevron', 'category_id': gas.id, 'priority': 10},
            {'pattern': 'bp gas', 'category_id': gas.id, 'priority': 10},
            {'pattern': 'gas station', 'category_id': gas.id, 'priority': 5},
        ])
    
    if streaming:
        rules.extend([
            {'pattern': 'netflix', 'category_id': streaming.id, 'priority': 10},
            {'pattern': 'spotify', 'category_id': streaming.id, 'priority': 10},
            {'pattern': 'hulu', 'category_id': streaming.id, 'priority': 10},
            {'pattern': 'disney+', 'category_id': streaming.id, 'priority': 10},
            {'pattern': 'hbo max', 'category_id': streaming.id, 'priority': 10},
        ])
    
    if fast_food:
        rules.extend([
            {'pattern': 'mcdonald', 'category_id': fast_food.id, 'priority': 10},
            {'pattern': 'burger king', 'category_id': fast_food.id, 'priority': 10},
            {'pattern': 'wendy', 'category_id': fast_food.id, 'priority': 10},
            {'pattern': 'taco bell', 'category_id': fast_food.id, 'priority': 10},
            {'pattern': 'chick-fil-a', 'category_id': fast_food.id, 'priority': 10},
        ])
    
    for rule_data in rules:
        existing = CategorizationRule.query.filter_by(pattern=rule_data['pattern']).first()
        if not existing:
            rule = CategorizationRule(
                pattern=rule_data['pattern'],
                match_type='contains',
                category_id=rule_data['category_id'],
                priority=rule_data['priority']
            )
            db.session.add(rule)
    
    db.session.commit()


def seed_default_user():
    """Seed a default development user."""
    existing = User.query.filter_by(username='admin').first()
    if not existing:
        user = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(user)
        db.session.commit()


def seed_database(app):
    """Seed all default data."""
    with app.app_context():
        seed_categories()
        seed_categorization_rules()
        seed_default_user()
        print("Database seeded successfully!")


if __name__ == '__main__':
    from backend.app import create_app
    app = create_app()
    init_db(app)
    seed_database(app)
