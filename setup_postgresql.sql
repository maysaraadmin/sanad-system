-- PostgreSQL Setup Script for Sanad System
-- Run this script in PostgreSQL as a superuser (postgres)

-- Create database
CREATE DATABASE sanad_db;

-- Create user with password
CREATE USER sanad_user WITH PASSWORD 'sanad_password';

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE sanad_db TO sanad_user;

-- Connect to the database and grant schema privileges
\c sanad_db;

-- Grant all privileges on schema public
GRANT ALL PRIVILEGES ON SCHEMA public TO sanad_user;

-- Grant sequence privileges
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sanad_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sanad_user;

-- Exit
\q
