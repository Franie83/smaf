# fix_all_missing_columns.py
from app import app, db
from sqlalchemy import text

def fix_all_tables():
    with app.app_context():
        # Fix admins table
        try:
            db.session.execute(text("ALTER TABLE admins ADD COLUMN IF NOT EXISTS mda VARCHAR(100)"))
            db.session.commit()
            print("✓ Added mda column to admins table")
        except Exception as e:
            print(f"! Error adding mda to admins: {e}")
            db.session.rollback()
        
        # Fix staff table
        try:
            db.session.execute(text("ALTER TABLE staff ADD COLUMN IF NOT EXISTS ed_password VARCHAR(200)"))
            db.session.commit()
            print("✓ Added ed_password column to staff table")
        except Exception as e:
            print(f"! Error adding ed_password to staff: {e}")
            db.session.rollback()
        
        try:
            db.session.execute(text("ALTER TABLE staff ADD COLUMN IF NOT EXISTS mda VARCHAR(100)"))
            db.session.commit()
            print("✓ Added mda column to staff table")
        except Exception as e:
            print(f"! Error adding mda to staff: {e}")
            db.session.rollback()
        
        # Fix users table (if it exists)
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mda VARCHAR(100)"))
            db.session.commit()
            print("✓ Added mda column to users table")
        except Exception as e:
            print(f"! Note: users.mda column: {e}")
            db.session.rollback()
        
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS edpassword VARCHAR(200)"))
            db.session.commit()
            print("✓ Added edpassword column to users table")
        except Exception as e:
            print(f"! Note: users.edpassword column: {e}")
            db.session.rollback()
        
        print("\n✅ Database migration completed successfully!")

if __name__ == "__main__":
    fix_all_tables()