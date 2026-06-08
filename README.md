# Bari Maintenance

A Django property maintenance management system for tracking rental income, expenses, and owner distributions.

---

## Requirements

- Python 3.10 or higher
- pip

---

## 1. Clone the Repository

```bash
git clone git@github.com:nobelna/bari-maintenance.git
cd bari-maintenance
```

---

## 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
```

**Activate on Linux / macOS:**
```bash
source venv/bin/activate
```

**Activate on Windows:**
```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install django openpyxl
```

---

## 4. Apply Database Migrations

```bash
python manage.py migrate
```

---

## 5. Seed Initial Data

This will load all units, expense categories, owners, and April 2026 sample data into the database, and create an admin user.

```bash
python manage.py seed_data
```

**Default admin credentials created by seed:**
| Username | Password  |
|----------|-----------|
| admin    | admin1234 |

---

## 6. (Optional) Create Additional Superusers

```bash
python manage.py createsuperuser
```

---

## 7. Run the Development Server

```bash
python manage.py runserver
```

Then open your browser and go to: **http://127.0.0.1:8000/**

You will be redirected to the login page. Sign in with your credentials.

---

## Pages

| URL | Description |
|-----|-------------|
| `/` | Dashboard — monthly summary |
| `/rental-income/` | Enter/edit monthly rent per unit |
| `/expenses/` | Enter/edit monthly expenses |
| `/distribution/` | View owner distributions and deductions |
| `/units/` | Manage property units |
| `/report/` | Printable monthly report (PDF / XLSX download) |
| `/admin/` | Django admin panel |

---

## Notes

- All pages require login. Unauthenticated users are redirected to `/accounts/login/`.
- The database is SQLite (`db.sqlite3`) stored locally — no external database needed.
- To reset the database and re-seed: delete `db.sqlite3`, run `python manage.py migrate`, then `python manage.py seed_data`.
