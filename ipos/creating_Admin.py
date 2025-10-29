# create_admin.py

from app import app, db
from model import User
from werkzeug.security import generate_password_hash

# Run inside the Flask application context
with app.app_context():
    # Make sure all database tables exist
    db.create_all()

    # Try to find existing admin user
    existing_admin = User.query.filter_by(username='admin').first()

    if existing_admin:
        print("⚠️  Admin user already exists — no new admin created.")
    else:
        # Create a new admin user with hashed password
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin'
        )

        # Add and commit to database
        db.session.add(admin_user)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print("   ➤ Username: admin")
        print("   ➤ Password: admin123")
        print("   ➤ Role: admin")
