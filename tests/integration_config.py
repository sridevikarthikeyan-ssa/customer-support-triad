"""
Configuration settings for integration tests.
These settings point to test/staging MongoDB collections to avoid
affecting production data during testing.
"""

# MongoDB Integration Test Settings
MONGODB_TEST_URI = "mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT"
MONGODB_TEST_DB = "customer_support_test"  # Use a dedicated test database
MONGODB_TEST_SOURCE_COLLECTION = "conversation_set_test"
MONGODB_TEST_TARGET_COLLECTION = "sentimental_analysis_test"

# Connection parameters for testing
MONGODB_TEST_PARAMS = {
    "maxPoolSize": 10,
    "minPoolSize": 1,
    "maxIdleTimeMS": 30000,
    "connectTimeoutMS": 5000,
    "serverSelectionTimeoutMS": 5000,
}

# Test batch processing settings
TEST_BATCH_SIZE = 5
TEST_MAX_RETRIES = 2