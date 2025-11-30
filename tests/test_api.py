"""Unit tests for the Personal Finance App API."""
import pytest
import json
from datetime import date, timedelta
from backend.app import create_app
from backend.models import db, Transaction, Category, Budget, User
from backend.db_init import seed_categories, seed_default_user
from backend.categorizer import categorize_transaction, rule_based_categorize


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        seed_categories()
        seed_default_user()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_transaction():
    """Sample transaction data."""
    return {
        'date': date.today().isoformat(),
        'amount': -25.50,
        'description': 'Coffee at Starbucks',
        'merchant': 'Starbucks'
    }


class TestTransactionsAPI:
    """Tests for transactions endpoints."""
    
    def test_list_transactions_empty(self, client):
        """Test listing transactions when empty."""
        response = client.get('/api/transactions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'transactions' in data
        assert data['total'] == 0
    
    def test_create_transaction(self, client, sample_transaction):
        """Test creating a transaction."""
        response = client.post(
            '/api/transactions',
            data=json.dumps(sample_transaction),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['description'] == sample_transaction['description']
        assert data['amount'] == sample_transaction['amount']
        assert data['id'] is not None
    
    def test_create_transaction_missing_fields(self, client):
        """Test creating a transaction with missing required fields."""
        response = client.post(
            '/api/transactions',
            data=json.dumps({'description': 'Test'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_get_transaction(self, client, sample_transaction):
        """Test getting a single transaction."""
        # Create transaction
        create_response = client.post(
            '/api/transactions',
            data=json.dumps(sample_transaction),
            content_type='application/json'
        )
        created = json.loads(create_response.data)
        
        # Get transaction
        response = client.get(f'/api/transactions/{created["id"]}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == created['id']
    
    def test_update_transaction(self, client, sample_transaction):
        """Test updating a transaction."""
        # Create transaction
        create_response = client.post(
            '/api/transactions',
            data=json.dumps(sample_transaction),
            content_type='application/json'
        )
        created = json.loads(create_response.data)
        
        # Update transaction
        response = client.put(
            f'/api/transactions/{created["id"]}',
            data=json.dumps({'amount': -30.00}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['amount'] == -30.00
    
    def test_delete_transaction(self, client, sample_transaction):
        """Test deleting a transaction."""
        # Create transaction
        create_response = client.post(
            '/api/transactions',
            data=json.dumps(sample_transaction),
            content_type='application/json'
        )
        created = json.loads(create_response.data)
        
        # Delete transaction
        response = client.delete(f'/api/transactions/{created["id"]}')
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f'/api/transactions/{created["id"]}')
        assert get_response.status_code == 404
    
    def test_list_transactions_with_filters(self, client, sample_transaction):
        """Test listing transactions with date filters."""
        # Create transaction
        client.post(
            '/api/transactions',
            data=json.dumps(sample_transaction),
            content_type='application/json'
        )
        
        # Filter by date range
        today = date.today().isoformat()
        response = client.get(f'/api/transactions?start_date={today}&end_date={today}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total'] >= 1


class TestCategoriesAPI:
    """Tests for categories endpoints."""
    
    def test_list_categories(self, client):
        """Test listing categories."""
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0  # Seed categories should exist
    
    def test_list_categories_flat(self, client):
        """Test listing categories in flat format."""
        response = client.get('/api/categories?flat=true')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_get_category_hierarchy(self, client):
        """Test getting category hierarchy."""
        response = client.get('/api/categories/hierarchy')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_create_category(self, client):
        """Test creating a category."""
        response = client.post(
            '/api/categories',
            data=json.dumps({
                'name': 'Test Category',
                'color': '#ff0000'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['name'] == 'Test Category'
    
    def test_create_duplicate_category(self, client):
        """Test creating a duplicate category."""
        category_data = {'name': 'Unique Category'}
        
        # Create first
        client.post(
            '/api/categories',
            data=json.dumps(category_data),
            content_type='application/json'
        )
        
        # Try to create duplicate
        response = client.post(
            '/api/categories',
            data=json.dumps(category_data),
            content_type='application/json'
        )
        assert response.status_code == 409


class TestBudgetsAPI:
    """Tests for budgets endpoints."""
    
    def test_list_budgets(self, client):
        """Test listing budgets."""
        response = client.get('/api/budgets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_create_budget(self, client):
        """Test creating a budget."""
        response = client.post(
            '/api/budgets',
            data=json.dumps({
                'name': 'Monthly Groceries',
                'amount': 500.00,
                'period': 'monthly'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['name'] == 'Monthly Groceries'
        assert data['amount'] == 500.00
    
    def test_budget_summary(self, client):
        """Test getting budget summary."""
        # Create a budget first
        client.post(
            '/api/budgets',
            data=json.dumps({
                'name': 'Test Budget',
                'amount': 100.00,
                'period': 'monthly'
            }),
            content_type='application/json'
        )
        
        response = client.get('/api/budgets/summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_budget' in data
        assert 'total_spending' in data


class TestReportsAPI:
    """Tests for reports endpoints."""
    
    def test_spending_by_category(self, client):
        """Test spending by category report."""
        today = date.today().isoformat()
        response = client.get(f'/api/reports/spending-by-category?start={today}&end={today}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
    
    def test_spending_over_time(self, client):
        """Test spending over time report."""
        end = date.today()
        start = end - timedelta(days=30)
        response = client.get(f'/api/reports/spending-over-time?start={start.isoformat()}&end={end.isoformat()}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'labels' in data
        assert 'datasets' in data
    
    def test_income_vs_expense(self, client):
        """Test income vs expense report."""
        end = date.today()
        start = end - timedelta(days=90)
        response = client.get(f'/api/reports/income-vs-expense?start={start.isoformat()}&end={end.isoformat()}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
    
    def test_summary(self, client):
        """Test summary report."""
        today = date.today().isoformat()
        response = client.get(f'/api/reports/summary?start={today}&end={today}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_income' in data
        assert 'total_expense' in data
        assert 'net' in data


class TestCSVImport:
    """Tests for CSV import endpoint."""
    
    def test_import_no_file(self, client):
        """Test import with no file."""
        response = client.post('/api/import-csv')
        assert response.status_code == 400
    
    def test_import_preview(self, client):
        """Test CSV import preview mode."""
        csv_content = "Date,Amount,Description\n2025-01-01,-25.00,Test Transaction"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode('utf-8')), 'test.csv')
        }
        
        response = client.post(
            '/api/import-csv',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['mode'] == 'preview'
        assert 'headers' in result
        assert 'suggested_mapping' in result


class TestCategorizer:
    """Tests for the categorization engine."""
    
    def test_rule_based_categorize(self, app):
        """Test rule-based categorization."""
        with app.app_context():
            # First seed the categorization rules
            from backend.db_init import seed_categorization_rules
            seed_categorization_rules()
            
            # Test Starbucks -> Coffee Shops
            result = rule_based_categorize('starbucks coffee purchase')
            assert result is not None
            
            # Verify it's the coffee category
            category = db.session.get(Category, result)
            assert category is not None
            assert 'coffee' in category.name.lower() or 'starbucks' in category.name.lower()
    
    def test_categorize_transaction(self, app):
        """Test full transaction categorization."""
        with app.app_context():
            # Test with known merchant
            category_id = categorize_transaction('Walmart Grocery', 'WALMART')
            assert category_id is not None
    
    def test_categorize_unknown(self, app):
        """Test categorization of unknown transaction."""
        with app.app_context():
            # Should return Uncategorized category
            category_id = categorize_transaction('Unknown XYZ123 Purchase')
            if category_id:
                category = db.session.get(Category, category_id)
                assert category.name == 'Uncategorized'


class TestAuth:
    """Tests for authentication endpoints."""
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'admin',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
    
    def test_login_failure(self, client):
        """Test failed login."""
        response = client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'admin',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_logout(self, client):
        """Test logout."""
        response = client.post('/api/auth/logout')
        assert response.status_code == 200


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestFrontendRoutes:
    """Tests for frontend routes."""
    
    def test_dashboard(self, client):
        """Test dashboard page."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_transactions_page(self, client):
        """Test transactions page."""
        response = client.get('/transactions')
        assert response.status_code == 200
    
    def test_categories_page(self, client):
        """Test categories page."""
        response = client.get('/categories')
        assert response.status_code == 200
    
    def test_budgets_page(self, client):
        """Test budgets page."""
        response = client.get('/budgets')
        assert response.status_code == 200
    
    def test_reports_page(self, client):
        """Test reports page."""
        response = client.get('/reports')
        assert response.status_code == 200
    
    def test_import_page(self, client):
        """Test import page."""
        response = client.get('/import')
        assert response.status_code == 200
