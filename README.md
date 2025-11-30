# Personal Finance App

A full-stack personal finance web application built with Flask backend, SQLite database, and Jinja2+Bootstrap frontend. Track transactions, manage budgets, categorize spending, and visualize financial reports with interactive charts.

## Features

- **Transaction Management**: CRUD operations for financial transactions with automatic categorization
- **Category System**: Hierarchical categories with customizable icons and colors
- **Budget Tracking**: Set and monitor budgets by category with spending alerts
- **Financial Reports**: Interactive charts including pie, donut, line, bar, stacked area, and histogram
- **CSV Import**: Import transactions from bank exports with automatic column detection and mapping
- **Rule-Based Categorization**: Configurable rules for automatic transaction categorization
- **ML Classifier Stub**: Ready-to-integrate machine learning categorization module

## Quick Start

### Windows

1. Double-click `run.bat` or run from command prompt:
   ```cmd
   run.bat
   ```

2. Open http://localhost:5000 in your browser

### Linux/macOS

1. Create virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Initialize database and run the app:
   ```bash
   export FLASK_ENV=development
   python -c "from backend.app import create_app; from backend.db_init import seed_database; app = create_app(); seed_database(app)"
   python -m flask --app backend.app run --host=0.0.0.0 --port=5000
   ```

3. Open http://localhost:5000 in your browser

### Docker

1. Build the Docker image:
   ```bash
   docker build -t finance-app .
   ```

2. Run the container:
   ```bash
   docker run -p 5000:5000 -v finance-data:/app/data finance-app
   ```

3. Open http://localhost:5000 in your browser

## Project Structure

```
finance-app/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── transactions.py   # Transaction CRUD
│   │   ├── categories.py     # Category management
│   │   ├── budgets.py        # Budget CRUD and summary
│   │   ├── reports.py        # Chart data endpoints
│   │   └── import_csv.py     # CSV import with mapping
│   ├── app.py                # Flask app factory
│   ├── config.py             # Configuration classes
│   ├── models.py             # SQLAlchemy models
│   ├── db_init.py            # Database initialization
│   └── categorizer.py        # Categorization engine
├── frontend/
│   ├── templates/            # Jinja2 templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── transactions.html
│   │   ├── transaction_form.html
│   │   ├── categories.html
│   │   ├── budgets.html
│   │   ├── reports.html
│   │   └── import.html
│   └── static/
│       ├── css/styles.css
│       └── js/main.js
├── tests/
│   └── test_api.py           # Unit tests
├── data/                     # SQLite database location
├── .github/workflows/
│   └── python-app.yml        # CI workflow
├── requirements.txt
├── run.bat                   # Windows launcher
├── Dockerfile
├── .gitignore
├── LICENSE
└── README.md
```

## API Endpoints

### Transactions
- `GET /api/transactions` - List transactions with filters
- `GET /api/transactions/{id}` - Get single transaction
- `POST /api/transactions` - Create transaction
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction

### Categories
- `GET /api/categories` - List categories (hierarchical or flat)
- `GET /api/categories/hierarchy` - Get full hierarchy
- `POST /api/categories` - Create category
- `PUT /api/categories/{id}` - Update category
- `DELETE /api/categories/{id}` - Delete category

### Budgets
- `GET /api/budgets` - List budgets with spending
- `GET /api/budgets/summary` - Budget vs spending summary
- `POST /api/budgets` - Create budget
- `PUT /api/budgets/{id}` - Update budget
- `DELETE /api/budgets/{id}` - Delete budget

### Reports
- `GET /api/reports/spending-by-category` - Pie/donut chart data
- `GET /api/reports/spending-over-time` - Line chart data
- `GET /api/reports/income-vs-expense` - Bar chart data
- `GET /api/reports/category-trend` - Stacked area chart data
- `GET /api/reports/spending-histogram` - Histogram data
- `GET /api/reports/summary` - Overall financial summary

### CSV Import
- `POST /api/import-csv` - Upload and import CSV file

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/auth/register` - Register new user

## Testing

Run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=term-missing
```

## API Examples

### Create a transaction
```bash
curl -X POST http://localhost:5000/api/transactions \
  -H "Content-Type: application/json" \
  -d '{"date":"2025-01-15","amount":-25.50,"description":"Coffee at Starbucks"}'
```

### List transactions
```bash
curl http://localhost:5000/api/transactions
```

### Import CSV
```bash
curl -F "file=@bank_export.csv" http://localhost:5000/api/import-csv
```

### Get spending report
```bash
curl "http://localhost:5000/api/reports/spending-by-category?start=2025-01-01&end=2025-01-31"
```

## Default Credentials

For development, a default user is created:
- Username: `admin`
- Password: `admin123`

⚠️ **Change these credentials in production!**

## Configuration

Environment variables:
- `FLASK_ENV` - development, production, or testing
- `SECRET_KEY` - Flask secret key (change in production)
- `DATABASE_PATH` - Path to SQLite database file

## Technologies Used

- **Backend**: Flask, Flask-SQLAlchemy, Werkzeug
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Jinja2 templates, Bootstrap 5, Chart.js
- **Testing**: pytest, pytest-cov
- **CI/CD**: GitHub Actions

## License

MIT License - see [LICENSE](LICENSE) file for details.
