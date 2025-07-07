# Sanad System

A Django-based system for managing and studying hadith chains of narrations (asanid).

## Features

- Hadith management with full text search
- Narrator database with reliability ratings
- Sanad (chain of narration) visualization
- User authentication and authorization
- Multi-language support (Arabic/English)
- Responsive design

## Prerequisites

- Python 3.8+
- PostgreSQL (recommended) or SQLite
- Tesseract OCR (optional, for text extraction)
- Poppler (for PDF processing)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sanad_system.git
   cd sanad_system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file and configure your environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your configuration.

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Configuration

### Required Environment Variables

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection URL (optional, for PostgreSQL)

### Optional Environment Variables

- `EMAIL_*`: For email configuration
- `REDIS_URL`: For caching and background tasks

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
black .
flake8
isort .
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure a production database
- [ ] Set up a proper web server (Nginx/Apache)
- [ ] Configure HTTPS
- [ ] Set up proper logging
- [ ] Configure backups

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request
