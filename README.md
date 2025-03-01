# Document-Scanning-System-Design-project
To run this application:

1.Create a directory structure:
project/
├── templates/
│   ├── login.html
│   ├── profile.html
│   └── analytics.html
├── uploads/
└── app.py

2.Install required packages:
pip install flask

3.Run the application
python app.py

->This implementation includes:User registration/login with basic authentication
Credit system with daily reset (20 credits)
Document scanning with basic similarity matching using SequenceMatcher
Profile page showing credits and past scans
Admin analytics dashboard
Basic API endpoints
Local file storage
SQLite database

->Limitations and notes:
Passwords are hashed with SHA-256 (in production, use bcrypt)
Similarity matching is basic (SequenceMatcher); for better results, you could integrate AI models
Credit request approval isn't implemented (would need admin interface)
No input validation/sanitization (add in production)
Session management is basic
Error handling is minimal
