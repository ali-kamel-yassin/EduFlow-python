# Database Setup Guide

## 🚀 MySQL Setup (Required)

This application requires a MySQL database.

### Step 1: Install MySQL
Ensure you have MySQL installed on your machine or have access to a remote MySQL server.

### Step 2: Create Database
Create a new database for the application:
```sql
CREATE DATABASE school_db;
```

### Step 3: Configure Environment Variables
Create a `.env` file in your project root and add your MySQL connection details:
```bash
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=school_db
MYSQL_PORT=3306
JWT_SECRET=your_strong_secret_key_here
NODE_ENV=development
```

### Step 4: Run the Application
```bash
pip install -r requirements.txt
python server.py
```

The app will:
- ✅ Connect to MySQL using the provided credentials
- ✅ Automatically create tables and default admin user

### Step 5: Deployment
1. Push your code to GitHub.
2. Set environment variables in your hosting dashboard (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, etc.).
3. ✅ Your data will now persist permanently!

## 🔒 Security Notes

### Generate Strong JWT Secret
Use a strong random string for `JWT_SECRET`. You can generate one:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Database Security
- ✅ Use strong passwords for MySQL.
- ✅ Ensure MySQL is not publicly accessible if possible.

## 🔄 Migration
If you have existing data, you should export it from your previous database and import it into MySQL.

## 🆘 Troubleshooting

### Connection Issues
- Check that MySQL credentials are correct.
- Ensure the MySQL server is running and accessible.
- Verify that the database name exists.

## 🎉 Benefits of This Setup

✅ **Permanent Data Storage** - No more data loss on restarts  
✅ **Scalable** - MySQL can handle thousands of students  
✅ **Industry Standard** - Widely used and supported  

Your school management system is now production-ready! 🎓