"""Flask application factory and main entry point."""
import os
from flask import Flask, render_template, send_from_directory
from backend.config import config
from backend.models import db


def create_app(config_name=None):
    """Create and configure the Flask application.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
    
    Returns:
        Configured Flask application
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static'
    )
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure data directory exists
    data_dir = os.path.dirname(app.config['DATABASE_PATH'])
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register API blueprints
    from backend.api.auth import auth_bp
    from backend.api.transactions import transactions_bp
    from backend.api.categories import categories_bp
    from backend.api.budgets import budgets_bp
    from backend.api.reports import reports_bp
    from backend.api.import_csv import import_csv_bp
    from backend.api.ml_training import ml_bp  # NEW
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(budgets_bp, url_prefix='/api/budgets')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(import_csv_bp, url_prefix='/api/import-csv')
    app.register_blueprint(ml_bp, url_prefix='/api/ml')  # NEW
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register frontend routes
    @app.route('/')
    def dashboard():
        """Render the dashboard page."""
        return render_template('dashboard.html')
    
    @app.route('/transactions')
    def transactions():
        """Render the transactions page."""
        return render_template('transactions.html')
    
    @app.route('/transactions/new')
    def new_transaction():
        """Render the new transaction form."""
        return render_template('transaction_form.html')
    
    @app.route('/transactions/<int:transaction_id>/edit')
    def edit_transaction(transaction_id):
        """Render the edit transaction form."""
        return render_template('transaction_form.html', transaction_id=transaction_id)
    
    @app.route('/categories')
    def categories():
        """Render the categories page."""
        return render_template('categories.html')
    
    @app.route('/budgets')
    def budgets():
        """Render the budgets page."""
        return render_template('budgets.html')
    
    @app.route('/reports')
    def reports():
        """Render the reports page."""
        return render_template('reports.html')
    
    @app.route('/import')
    def import_page():
        """Render the CSV import page."""
        return render_template('import.html')
    
    @app.route('/ml-training')
    def ml_training():
        """Render the ML training page."""
        return render_template('ml_training.html')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy'}, 200
    
    return app


# Create app instance for running directly
app = create_app()


if __name__ == '__main__':
    # Initialize database and seed data
    from backend.db_init import seed_database
    seed_database(app)
    
    # Run the development server
    # Note: debug=True should only be used in development environments
    # In production, use a proper WSGI server like gunicorn
    import os
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
