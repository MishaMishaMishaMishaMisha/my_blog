# My Blog
A full-stack blogging platform built primarily to practice backend development with Python and FastAPI.

The application allows users to create and manage blog posts, leave comments, upload media, and manage their accounts. The main focus of the project was backend architecture, asynchronous programming, database interaction, authentication, background task processing, caching, testing, and containerization.

The frontend was built with Vue.js.

# Features
## Authentication & User Management

- User registration and login
- JWT-based authentication with access and refresh tokens
- Email account verification
- Password reset via email
- Profile viewing and editing
- User profile pages
- Protected endpoints for authenticated users

## Posts
- Create, edit, and delete posts
- View posts created by other users
- Search posts by title, author, and tags
- Post pagination and sorting
- Post view counter
- Tags
- Media attachments in posts
- Reactions to posts

## Comments
- Add comments to posts
- Edit and delete own comments
- Reply to other users with nested comments
- Reactions to comments
- Media attachments in comments

## Background Processing
Celery is used for tasks that should not block HTTP requests:
- Sending emails
- Cleaning up unused media files
- Synchronizing post view counters between Redis and PostgreSQL

# Infrastructure
The application is containerized with Docker Compose and consists of several services:
- FastAPI application
- PostgreSQL
- Redis
- Celery worker
- Celery Beat
- Nginx
- Vue.js frontend

Nginx is used as a reverse proxy, serves static/media files, and handles response compression.

# Tech Stack

## Backend
- Python
- FastAPI
- SQLAlchemy
- asyncpg
- PostgreSQL
- Alembic
- Redis
- Celery
- JWT
- Pytest
  
## Frontend
- Vue.js
- Vite
- JavaScript / TypeScript
  
## DevOps
- Docker
- Docker Compose
- Nginx
- GitHub Actions
- uv

## Testing
The main backend functionality is covered by automated tests using Pytest.

A separate Docker Compose configuration is used for the test environment, including a separate test database and environment configuration.

## CI/CD
The repository includes a GitHub Actions CI/CD pipeline.

On pushes and pull requests to the main branch, the pipeline runs:
1. Application build
2. Automated tests

After successful CI checks, deployment can be triggered manually.

The deployment workflow builds and starts the application using Docker Compose in a Linux environment. The workflow is designed so that the same deployment approach can be used on a Linux server with Docker installed.

# Local Setup
## Requirements
Make sure the following tools are installed:
- Git
- Docker
- Docker Compose
- uv
- Node.js and npm
  
## 1. Clone the repository
git clone https://github.com/MishaMishaMishaMishaMisha/my_blog.git

cd my_blog

## 2. Install backend dependencies
uv sync

## 3. Install frontend dependencies
cd frontend

npm install

cd ..

## 4. Configure environment variables
Create the backend .env file from .env.example

Create the frontend .env file from the corresponding example file in the frontend directory.

Configure the required database, Redis, JWT, email, and other application settings.

## 5. Start the application
### Development
docker compose -f docker-compose-dev.yaml up --build -d

### Production
docker compose -f docker-compose-prod.yaml up --build -d

## 6. Run tests
Create .test.env using .env as a template and configure the test environment.

Then run:

docker compose --env-file .test.env -f docker-compose-test.yaml run --rm my_app_test uv run pytest

# Screenshots
### 1
<img width="1919" height="815" alt="1" src="https://github.com/user-attachments/assets/033ffc12-bbc9-4b7a-bb1c-3d2d584fab20" />

### 2
<img width="1919" height="869" alt="2" src="https://github.com/user-attachments/assets/138830fc-6086-4f09-8b0c-24807666e59c" />

### 3
<img width="1915" height="537" alt="3" src="https://github.com/user-attachments/assets/e6cdb070-d8ad-43af-b7be-a216f4991f31" />

### 4
<img width="1917" height="871" alt="4" src="https://github.com/user-attachments/assets/1cebdf37-d65a-4c51-979c-e4dcdfc74b9a" />

### 5
<img width="887" height="864" alt="5" src="https://github.com/user-attachments/assets/613a27f1-5f29-4c12-acc7-cdb8ae92d5eb" />

### 6
<img width="995" height="874" alt="6" src="https://github.com/user-attachments/assets/8af05425-d8ba-4516-8633-54106887f49a" />

### 7
<img width="893" height="837" alt="7" src="https://github.com/user-attachments/assets/d1c15db7-3da2-49f3-92da-03b6d637c97b" />

### 8
<img width="1914" height="337" alt="8" src="https://github.com/user-attachments/assets/0f549072-4fbb-429f-8257-83bd67626d26" />

### 9
<img width="1919" height="714" alt="9" src="https://github.com/user-attachments/assets/4164dce3-f05c-407c-a64e-c0aeaa1d49a1" />

### 10
<img width="1919" height="468" alt="10" src="https://github.com/user-attachments/assets/8fb6d96c-06bf-4c11-a855-376fc258e532" />


