# Django Project Commands Reference

## Server Access

### Backend Server

```
ssh -i keys/propertyfinder.pem ubuntu@
```

Purpose: Login to the backend server using SSH with a specified key file.

### Database Server

```
ssh -i keys/propertyfinder.pem ubuntu@3.83.30.251
```

Purpose: Login to the database server using SSH with a specified key file.

### Database Setup

```
sudo apt update && sudo apt upgrade -y
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install postgresql postgresql-contrib -y
psql --version
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Purpose: Install the PostgreSQL server, initialize the database, and start the PostgreSQL service

## PostgreSQL Database Management

### Database Access

```
sudo -u postgres psql
```

Purpose: Connect to the PostgreSQL interactive terminal as the postgres user

### Database Access

```
CREATE DATABASE analysisdb;
CREATE USER danai WITH SUPERUSER PASSWORD 'my_password';
GRANT ALL PRIVILEGES ON DATABASE analysisdb TO danai;
\q
```

Purpose: Create the propertyanalysisdb database and the danai user with superuser privileges

### Configuration

```
sudo nano /etc/postgresql/[version]/main/postgresql.conf
```

```
listen_addresses = '*'          # what IP address(es) to listen on;
port = 5432                             # (change requires restart)
```

Purpose: Edit the PostgreSQL configuration file to add IP addresses to the allowed list.

```
sudo nano /var/lib/pgsql/data/pg_hba.conf
```

```
host    all             all             0.0.0.0/0               md5
```

Purpose: Edit the PostgreSQL configuration file to add IP addresses to the allowed list.

### Service Management

```
sudo systemctl restart postgresql
```

Purpose: Restart the PostgreSQL service after making configuration changes.

### Database Access

```
sudo -u postgres psql -d propertyanalysisdb
```

Purpose: Access the 'propertyanalysisdb' database as the 'postgres' user.

```
psql -h localhost -U danai -d propertyanalysisdb
```

Purpose: Access the 'propertyanalysisdb' database as danai.

### User Management

```
\du
```

Purpose: List all database users and their roles.

```
CREATE USER danai WITH SUPERUSER PASSWORD 'my_password';
```

Purpose: Create a new superuser named 'danai' with a specified password.

```
ALTER USER danai WITH SUPERUSER;
```

Purpose: Grant superuser privileges to the 'danai' user.

### Database Operations

```
DROP DATABASE propertyanalysisdb;
CREATE DATABASE propertyanalysisdb;
```

Purpose: Delete and recreate the 'propertyanalysisdb' database.

### Privilege Management

```
GRANT ALL PRIVILEGES ON DATABASE propertyanalysisdb TO danai;
```

Purpose: Grant all privileges on the 'propertyanalysisdb' database to user 'danai'.

```
\c propertyanalysisdb
GRANT ALL PRIVILEGES ON SCHEMA public TO danai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO danai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO danai;
```

Purpose: Connect to 'propertyanalysisdb' and grant all privileges on the public schema, tables, and sequences to user 'danai'.

### Exiting psql

```
\q
```

Purpose: Exit the PostgreSQL interactive terminal.

## Notes

- Always ensure you have the necessary permissions before running these commands.
- Be cautious when using superuser privileges and granting extensive permissions.
- Regularly backup your database before making significant changes.
- Keep your SSH key secure and never share it publicly.
