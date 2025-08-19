import os

def create_tables():
    print("DEBUG: Using dummy create_tables. No tables will be created.")
    pass

class MockCursor:
    def execute(self, *args, **kwargs):
        pass

    def fetchone(self, *args, **kwargs):
        return None

    def fetchall(self, *args, **kwargs):
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockConnection:
    def cursor(self, *args, **kwargs):
        return MockCursor()

    def commit(self, *args, **kwargs):
        pass

def get_db():
    print("DEBUG: Using dummy get_db. No real database connection.")
    return MockConnection()
