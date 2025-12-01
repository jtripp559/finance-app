"""Machine Learning-based transaction categorization using scikit-learn."""
import os
import pickle
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from backend.models import db, Category, Transaction


class MLCategorizer:
    """ML-based transaction categorizer using TF-IDF and Random Forest."""
    
    def __init__(self, model_dir='models'):
        """Initialize the ML categorizer."""
        self.model_dir = model_dir
        self.vectorizer = None
        self.classifier = None
        self.category_mapping = None
        self.reverse_mapping = None
        
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        self.load_model()
    
    def preprocess_text(self, text):
        """Preprocess merchant/description text - extract core merchant name."""
        if not text:
            return ""
        
        text = str(text).lower()
        
        # Remove common bank transaction prefixes
        prefixes_to_remove = [
            r'^withdrawal[-\s]*@?\s*',
            r'^deposit[-\s]*@?\s*',
            r'^withdrawal-ach-a-\S*\s*',
            r'^deposit-ach-a-\S*\s*',
            r'^withdrawal-transfer-\S*\s*',
            r'^web',  # Remove WEB prefix (WEBVENMO -> VENMO)
        ]
        
        for pattern in prefixes_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove noise patterns
        noise_patterns = [
            r'\d{6,}',  # Long numbers (account numbers, trace numbers)
            r'#\d+',    # Store numbers like #1360
            r'\(\d+\)', # Numbers in parentheses like (PAY 091536)
            r'\([^)]*\)',  # Anything in parentheses - often noise
            r'trace\s*#?\s*\d+',
            r'eff\.?\s*date.*',
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # Dates
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # Phone numbers
            r'\b[a-z]{2}\s+us\b',  # State codes like "CA US"
            r'\bus\b$',
            r'\bca\b$',
            r'online\s*access',
            r'transfer\s*(std|dts)',
            r'from\s+share\s+\d+',
            r'to\s+share\s+\d+',
            r'item\s*#?\d+',
            r'ro\s*\d+',  # Remove "RO 27" type patterns
            r'\d+\s*[a-z]\s+[a-z]+\s+(ave?|st|rd|blvd|dr|way)',  # Addresses
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def get_training_data(self):
        """Get training data from predefined merchant list and database transactions."""
        
        # First, get all categories from database to know what's available
        db_categories = {cat.name: cat.id for cat in Category.query.all()}
        
        # Helper to get category ID, trying multiple names
        def get_cat_id(*names):
            for name in names:
                if name in db_categories:
                    return db_categories[name]
            return None
        
        # Build training data dynamically based on available categories
        training_entries = []
        
        # === AUTO INSURANCE ===
        auto_ins_id = get_cat_id('Auto Insurance', 'Insurance')
        if auto_ins_id:
            for merchant in [
                'state farm', 'state farm ro', 'sfpp', 'state farm sfpp',
                'allstate', 'geico', 'progressive', 'farmers insurance',
                'liberty mutual', 'nationwide', 'usaa', 'american family',
                'travelers', 'esurance', 'the general', 'root insurance',
            ]:
                training_entries.append((merchant, auto_ins_id))
        
        # === HEALTH INSURANCE ===
        health_ins_id = get_cat_id('Health Insurance', 'Insurance', 'Medical')
        if health_ins_id:
            for merchant in [
                'aetna', 'blue cross', 'blue shield', 'united healthcare',
                'cigna', 'humana', 'kaiser', 'anthem', 'health insurance',
            ]:
                training_entries.append((merchant, health_ins_id))
        
        # === GROCERIES ===
        groceries_id = get_cat_id('Groceries')
        if groceries_id:
            for merchant in [
                'walmart', 'walmart supercenter', 'target', 'kroger', 'safeway',
                'albertsons', 'publix', 'whole foods', 'trader joes', 'trader joe',
                'aldi', 'costco', 'costco whse', 'costco wholesale', 'sams club',
                'food 4 less', 'food4less', 'food lion', 'heb', 'meijer', 'wegmans',
                'sprouts', 'winco', 'grocery', 'north fresno grocery', 'instacart',
                'groceries', 'supermarket', 'market',
            ]:
                training_entries.append((merchant, groceries_id))
        
        # === RESTAURANTS ===
        restaurants_id = get_cat_id('Restaurants')
        if restaurants_id:
            for merchant in [
                'restaurant', 'olive garden', 'applebees', 'chilis', 'red lobster',
                'outback', 'texas roadhouse', 'buffalo wild wings', 'dennys', 'ihop',
                'cheesecake factory', 'panera', 'chipotle', 'qdoba', 'subway',
                'cafe rio', 'papa murphys', 'papa murphy', 'uber eats', 'doordash',
                'grubhub', 'postmates', 'kona ice', 'dining', 'grill', 'bistro',
            ]:
                training_entries.append((merchant, restaurants_id))
        
        # === COFFEE SHOPS ===
        coffee_id = get_cat_id('Coffee Shops')
        if coffee_id:
            for merchant in [
                'starbucks', 'dunkin', 'peets coffee', 'dutch bros', 'coffee',
                'cafe', 'espresso', 'caribou coffee', 'tim hortons',
            ]:
                training_entries.append((merchant, coffee_id))
        
        # === FAST FOOD ===
        fast_food_id = get_cat_id('Fast Food')
        if fast_food_id:
            for merchant in [
                'mcdonalds', 'burger king', 'wendys', 'taco bell', 'kfc',
                'popeyes', 'chick fil a', 'chickfila', 'five guys', 'in n out',
                'jack in the box', 'sonic', 'arbys', 'carls jr', 'hardees',
            ]:
                training_entries.append((merchant, fast_food_id))
        
        # === GAS ===
        gas_id = get_cat_id('Gas')
        if gas_id:
            for merchant in [
                'shell', 'exxon', 'chevron', 'bp', 'texaco', 'speedway',
                'circle k', '7 eleven', '7eleven', 'gas station', 'fuel',
                'valero', 'arco', 'mobil', 'marathon', 'sunoco',
            ]:
                training_entries.append((merchant, gas_id))
        
        # === UTILITIES ===
        utilities_id = get_cat_id('Utilities')
        if utilities_id:
            for merchant in [
                'pgande', 'pge', 'pg e', 'pge ez pay', 'pacific gas', 'electric',
                'power company', 'water', 'city of clovis', 'city of fresno',
                'comcast', 'xfinity', 'verizon', 'at t', 'att', 't mobile', 'tmobile',
                'spectrum', 'cox', 'frontier', 'utility', 'utilities',
            ]:
                training_entries.append((merchant, utilities_id))
        
        # === RENT/MORTGAGE ===
        mortgage_id = get_cat_id('Rent/Mortgage')
        if mortgage_id:
            for merchant in [
                'freedom', 'freedom mortgage', 'freedom mtg', 'mtg pymts', 'mortgage',
                'rent', 'quicken loans', 'rocket mortgage', 'lease', 'housing',
            ]:
                training_entries.append((merchant, mortgage_id))
        
        # === TRANSFERS ===
        transfers_id = get_cat_id('Transfers')
        if transfers_id:
            for merchant in [
                'venmo', 'venmo payment', 'venmo cashout', 'tech cu', 'amex epayment',
                'american express', 'target card srvc', 'chase credit crd', 'chase autopay',
                'citi thankyou', 'macys', 'shop your way mc', 'sears payment', 'sears click2pay',
                'atm', 'atmxl', 'withdrawal transfer', 'tsdl', 'transfer std', 'transfer dts',
                'pacific service cu', 'eecu', 'credit card payment', 'payment',
            ]:
                training_entries.append((merchant, transfers_id))
        
        # === SALARY ===
        salary_id = get_cat_id('Salary')
        if salary_id:
            for merchant in [
                'gusto', 'rrg operations', 'payroll', 'direct deposit', 'pay',
                'ramp reimburse', 'salary', 'wages', 'employer',
            ]:
                training_entries.append((merchant, salary_id))
        
        # === INVESTMENTS ===
        investments_id = get_cat_id('Investments')
        if investments_id:
            for merchant in [
                'robinhood', 'dividend', 'fidelity', 'vanguard', 'schwab',
                'etrade', 'td ameritrade', 'investment', 'brokerage',
            ]:
                training_entries.append((merchant, investments_id))
        
        # === MEDICAL ===
        medical_id = get_cat_id('Medical')
        if medical_id:
            for merchant in [
                'american benefit', 'claim pmt', 'hospital', 'medical', 'doctor',
                'dentist', 'dental', 'urgent care', 'newsome', 'optometrist',
                'frame doctors', 'clinic', 'physician', 'healthcare',
            ]:
                training_entries.append((merchant, medical_id))
        
        # === PHARMACY ===
        pharmacy_id = get_cat_id('Pharmacy')
        if pharmacy_id:
            for merchant in [
                'cvs', 'walgreens', 'rite aid', 'pharmacy', 'costco rx',
                'walmart pharmacy', 'drugstore',
            ]:
                training_entries.append((merchant, pharmacy_id))
        
        # === TAXES ===
        taxes_id = get_cat_id('Taxes')
        if taxes_id:
            for merchant in [
                'irs treas', 'irs', 'tax ref', 'tax refund', 'franchise tax bd',
                'casttaxrfd', 'state tax', 'federal tax', 'taxes',
            ]:
                training_entries.append((merchant, taxes_id))
        
        # === STREAMING ===
        streaming_id = get_cat_id('Streaming Services')
        if streaming_id:
            for merchant in [
                'netflix', 'spotify', 'hulu', 'disney plus', 'disney', 'hbo max',
                'amazon prime', 'apple tv', 'youtube premium', 'paramount',
                'peacock', 'crunchyroll',
            ]:
                training_entries.append((merchant, streaming_id))
        
        # === SUBSCRIPTIONS ===
        subscriptions_id = get_cat_id('Subscriptions')
        if subscriptions_id:
            for merchant in [
                'instacart subscription', 'slidesgo', 'privacycom', 'patreon',
                'github', 'dropbox', 'google one', 'icloud', 'microsoft 365',
                'adobe', 'canva', 'subscription',
            ]:
                training_entries.append((merchant, subscriptions_id))
        
        # === SHOPPING ===
        shopping_id = get_cat_id('Shopping', 'Clothing')
        if shopping_id:
            for merchant in [
                'amazon', 'amazon com', 'ebay', 'best buy', 'the book nook',
                'book nook', 'macys', 'nordstrom', 'kohls', 'target',
            ]:
                training_entries.append((merchant, shopping_id))
        
        # === HOME GOODS ===
        home_goods_id = get_cat_id('Home Goods')
        if home_goods_id:
            for merchant in [
                'home depot', 'lowes', 'ikea', 'fresno ag hardware', 'hardware',
                'bed bath', 'williams sonoma', 'pottery barn',
            ]:
                training_entries.append((merchant, home_goods_id))
        
        # === PET CARE ===
        pet_id = get_cat_id('Pet Care')
        if pet_id:
            for merchant in [
                'petco', 'petsmart', 'aquatic pets', 'veterinarian', 'vet',
                'animal hospital', 'pet grooming', 'pet',
            ]:
                training_entries.append((merchant, pet_id))
        
        # === ENTERTAINMENT ===
        entertainment_id = get_cat_id('Entertainment', 'Movies')
        if entertainment_id:
            for merchant in [
                'san joaquin valley', 'library', 'garden bros circus', 'circus',
                'amc', 'regal', 'cinemark', 'movie', 'theater', 'museum', 'zoo',
            ]:
                training_entries.append((merchant, entertainment_id))
        
        # === EDUCATION ===
        education_id = get_cat_id('Education')
        if education_id:
            for merchant in [
                'cusd', 'clovis adult', 'school', 'university', 'college',
                'udemy', 'coursera', 'education', 'tuition',
            ]:
                training_entries.append((merchant, education_id))
        
        # === PARKING ===
        parking_id = get_cat_id('Parking')
        if parking_id:
            for merchant in [
                'parkmobile', 'cof parcs', 'parking', 'park',
            ]:
                training_entries.append((merchant, parking_id))
        
        # === CAR MAINTENANCE ===
        car_maint_id = get_cat_id('Car Maintenance', 'Transportation')
        if car_maint_id:
            for merchant in [
                'jiffy lube', 'valvoline', 'oil change', 'car wash', 'auto repair',
                'mechanic', 'firestone', 'goodyear', 'pep boys', 'autozone',
            ]:
                training_entries.append((merchant, car_maint_id))
        
        # === PERSONAL CARE ===
        personal_id = get_cat_id('Personal Care')
        if personal_id:
            for merchant in [
                'gym', 'planet fitness', 'la fitness', 'salon', 'hair salon',
                'barber', 'nail salon', 'spa', 'massage', 'great clips',
            ]:
                training_entries.append((merchant, personal_id))
        
        # Build final training data
        texts = []
        labels = []
        
        for merchant, category_id in training_entries:
            processed = self.preprocess_text(merchant)
            if processed:
                texts.append(processed)
                labels.append(category_id)
        
        # Also include existing categorized transactions from database
        transactions = Transaction.query.filter(
            Transaction.category_id.isnot(None),
            Transaction.deleted_at.is_(None)
        ).all()
        
        for txn in transactions:
            if txn.merchant:
                processed = self.preprocess_text(txn.merchant)
                if processed:
                    texts.append(processed)
                    labels.append(txn.category_id)
            if txn.description:
                processed = self.preprocess_text(txn.description)
                if processed:
                    texts.append(processed)
                    labels.append(txn.category_id)
        
        return texts, labels
    
    def train(self, min_samples_per_category=2):
        """Train the ML model."""
        texts, labels = self.get_training_data()
        
        if len(texts) < 10:
            return {
                'success': False,
                'error': 'Insufficient training data. Need at least 10 samples.'
            }
        
        # Filter out categories with too few samples
        from collections import Counter
        label_counts = Counter(labels)
        valid_labels = {label for label, count in label_counts.items() if count >= min_samples_per_category}
        
        filtered_texts = []
        filtered_labels = []
        for text, label in zip(texts, labels):
            if label in valid_labels and text.strip():
                filtered_texts.append(text)
                filtered_labels.append(label)
        
        if len(filtered_texts) < 10:
            return {
                'success': False,
                'error': f'Insufficient samples per category.'
            }
        
        # Create category mapping
        unique_labels = sorted(list(set(filtered_labels)))
        self.category_mapping = {i: cat_id for i, cat_id in enumerate(unique_labels)}
        self.reverse_mapping = {cat_id: i for i, cat_id in self.category_mapping.items()}
        
        # Convert labels to indices
        y = [self.reverse_mapping[label] for label in filtered_labels]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            filtered_texts, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train TF-IDF vectorizer with better settings
        self.vectorizer = TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 3),
            min_df=1,
            sublinear_tf=True
        )
        X_train_vec = self.vectorizer.fit_transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)
        
        # Train Random Forest classifier
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=30,
            random_state=42,
            class_weight='balanced',
            min_samples_leaf=1
        )
        self.classifier.fit(X_train_vec, y_train)
        
        # Evaluate
        y_pred = self.classifier.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Get category names for report
        category_names = {}
        for i, cat_id in self.category_mapping.items():
            cat = Category.query.get(cat_id)
            if cat:
                category_names[i] = cat.name
        
        target_names = [category_names.get(i, f'Unknown_{i}') for i in range(len(self.category_mapping))]
        
        report = classification_report(y_test, y_pred, target_names=target_names, output_dict=True, zero_division=0)
        
        # Save model
        self.save_model()
        
        return {
            'success': True,
            'accuracy': round(accuracy, 4),
            'samples': len(filtered_texts),
            'categories': len(unique_labels),
            'report': report
        }
    
    def predict(self, text, confidence_threshold=0.15):
        """Predict category for a merchant/description.
        
        Lowered default threshold to 0.15 for more matches.
        """
        if not self.vectorizer or not self.classifier:
            return None, 0
        
        processed = self.preprocess_text(text)
        if not processed:
            return None, 0
        
        try:
            X = self.vectorizer.transform([processed])
            probabilities = self.classifier.predict_proba(X)[0]
            predicted_idx = probabilities.argmax()
            confidence = probabilities[predicted_idx]
            
            if confidence < confidence_threshold:
                return None, 0
            
            category_id = self.category_mapping[predicted_idx]
            return category_id, float(confidence)
        except Exception as e:
            print(f"Prediction error: {e}")
            return None, 0
    
    def save_model(self):
        """Save the trained model to disk."""
        if not self.vectorizer or not self.classifier:
            return False
        
        try:
            with open(os.path.join(self.model_dir, 'vectorizer.pkl'), 'wb') as f:
                pickle.dump(self.vectorizer, f)
            
            with open(os.path.join(self.model_dir, 'classifier.pkl'), 'wb') as f:
                pickle.dump(self.classifier, f)
            
            with open(os.path.join(self.model_dir, 'category_mapping.pkl'), 'wb') as f:
                pickle.dump(self.category_mapping, f)
            
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self):
        """Load the trained model from disk."""
        try:
            vectorizer_path = os.path.join(self.model_dir, 'vectorizer.pkl')
            classifier_path = os.path.join(self.model_dir, 'classifier.pkl')
            mapping_path = os.path.join(self.model_dir, 'category_mapping.pkl')
            
            if not all(os.path.exists(p) for p in [vectorizer_path, classifier_path, mapping_path]):
                return False
            
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            
            with open(classifier_path, 'rb') as f:
                self.classifier = pickle.load(f)
            
            with open(mapping_path, 'rb') as f:
                self.category_mapping = pickle.load(f)
            
            self.reverse_mapping = {cat_id: i for i, cat_id in self.category_mapping.items()}
            
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False


# Global instance
_ml_categorizer = None


def get_ml_categorizer():
    """Get or create the global ML categorizer instance."""
    global _ml_categorizer
    if _ml_categorizer is None:
        _ml_categorizer = MLCategorizer()
    return _ml_categorizer


def ml_categorize(merchant=None, description=None, confidence_threshold=0.15):
    """Categorize transaction using ML model.
    
    Lowered default threshold to 0.15 for more matches.
    """
    categorizer = get_ml_categorizer()
    
    # Try merchant first
    if merchant:
        category_id, confidence = categorizer.predict(merchant, confidence_threshold)
        if category_id:
            return category_id, confidence
    
    # Then description
    if description:
        category_id, confidence = categorizer.predict(description, confidence_threshold)
        if category_id:
            return category_id, confidence
    
    # Try combined
    combined = f"{merchant or ''} {description or ''}".strip()
    if combined:
        category_id, confidence = categorizer.predict(combined, confidence_threshold)
        if category_id:
            return category_id, confidence
    
    return None, 0


def train_ml_model():
    """Train or retrain the ML model."""
    categorizer = get_ml_categorizer()
    return categorizer.train()