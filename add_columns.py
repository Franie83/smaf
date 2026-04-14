# add_columns.py
from app import app, db
from sqlalchemy import text

def add_missing_columns():
    with app.app_context():
        # Check and add ed_password to staff table
        try:
            db.session.execute(text("ALTER TABLE staff ADD COLUMN IF NOT EXISTS ed_password VARCHAR(200)"))
            db.session.commit()
            print("✓ Added ed_password column to staff table")
        except Exception as e:
            print(f"! Could not add ed_password: {e}")
            db.session.rollback()
        
        # Check and add mda to staff table
        try:
            db.session.execute(text("ALTER TABLE staff ADD COLUMN IF NOT EXISTS mda VARCHAR(100)"))
            db.session.commit()
            print("✓ Added mda column to staff table")
        except Exception as e:
            print(f"! Could not add mda to staff: {e}")
            db.session.rollback()
        
        # Check and add mda to users table
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mda VARCHAR(100)"))
            db.session.commit()
            print("✓ Added mda column to users table")
        except Exception as e:
            print(f"! Could not add mda to users: {e}")
            db.session.rollback()
        
        # Check and add edpassword to users table
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS edpassword VARCHAR(200)"))
            db.session.commit()
            print("✓ Added edpassword column to users table")
        except Exception as e:
            print(f"! Could not add edpassword to users: {e}")
            db.session.rollback()
        
        print("\n✅ Database migration completed!")

if __name__ == "__main__":
    add_missing_columns()