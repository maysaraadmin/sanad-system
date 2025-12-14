# PostgreSQL Setup Guide for Sanad System

## Prerequisites
- PostgreSQL installed on your system
- Python virtual environment activated
- psycopg2-binary already in requirements.txt

## Step 1: Install PostgreSQL (if not already installed)

### Windows:
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer and note the postgres password you set
3. Add PostgreSQL to PATH during installation

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS:
```bash
brew install postgresql
brew services start postgresql
```

## Step 2: Create Database and User

### Option A: Using the SQL script
```bash
# Log in to PostgreSQL as postgres user
psql -U postgres

# Run the setup script
\i setup_postgresql.sql
```

### Option B: Manual commands
```bash
# Log in to PostgreSQL
psql -U postgres

# Run these commands one by one:
CREATE DATABASE sanad_db;
CREATE USER sanad_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE sanad_db TO sanad_user;
\c sanad_db;
GRANT ALL PRIVILEGES ON SCHEMA public TO sanad_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sanad_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sanad_user;
\q
```

## Step 3: Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit `.env` with your actual database credentials:
```
DB_NAME=sanad_db
DB_USER=sanad_user
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432
```

## Step 4: Install Dependencies and Run Migrations

```bash
# Install dependencies (psycopg2-binary is already included)
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

## Step 5: Test the Connection

```bash
# Test Django connection
python manage.py dbshell

# Or run the development server
python manage.py runserver
```

## Troubleshooting

### Connection Issues:
- Ensure PostgreSQL service is running
- Check that the database and user exist
- Verify password in `.env` matches what you set
- Check firewall settings if using remote PostgreSQL

### Migration Issues:
- If migrating from SQLite, you may need to reset migrations:
  ```bash
  python manage.py migrate --fake-initial
  ```

### Performance Tips:
- For production, consider:
  - Setting `DB_HOST` to your PostgreSQL server
  - Using connection pooling
  - Configuring PostgreSQL settings for your workload

## Production Considerations

1. **Security**: Use strong passwords and restrict database access
2. **Performance**: Tune PostgreSQL settings (shared_buffers, work_mem, etc.)
3. **Backups**: Set up regular database backups
4. **Monitoring**: Monitor database performance and connections

## Environment-Specific Settings

You can create different `.env` files for different environments:
- `.env.development` - for local development
- `.env.production` - for production deployment

Then load the appropriate file in your Django settings or deployment script.
