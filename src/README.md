# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Configure student and administrator accounts. Generate a salted password hash for each account:

   ```
   python -c "from getpass import getpass; from app import hash_password; print(hash_password(getpass()))"
   ```

   Set the `APP_USERS` environment variable to a JSON object containing each email, generated password hash, and role:

   ```json
   {
     "student@mergington.edu": {"password_hash": "<student-hash>", "role": "student"},
     "admin@mergington.edu": {"password_hash": "<admin-hash>", "role": "admin"}
   }
   ```

    Replace the placeholders with the generated hashes, then set `APP_USERS` in the same shell used to run the app. In PowerShell, use `$env:APP_USERS = '<JSON>'`; in bash, use `export APP_USERS='<JSON>'`. Keep account configuration out of source control. The app verifies PBKDF2 password hashes and issues in-memory bearer sessions that expire after 12 hours. Use HTTPS and shared session storage for a deployed multi-process application.

3. Run the application:

   ```
   python app.py
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| POST   | `/auth/login`                                                      | Verify credentials and receive a bearer token                       |
| POST   | `/auth/logout`                                                     | Revoke the current bearer token                                     |
| GET    | `/activities`                                                     | List activities for an authenticated user                           |
| POST   | `/activities/{activity_name}/signup`                              | Sign up the authenticated student                                   |
| DELETE | `/activities/{activity_name}/participants/{email}`                | Remove your own registration or, as an admin, any registration       |

Students can see their own registrations; administrators can see all participants. Activity browsing, registration, and participant management require a valid bearer token.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
