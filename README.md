# Automated-Traffic-Management

## Project Overview
Django web application which represent system that monitors all vehicles in the city and specifically in major juncions 

## Collaborators
Jalal Mammadov

Laurent Bialylew

## Requirements
*[Django](https://www.djangoproject.com/)

*[Python 3.11](https://www.python.org/downloads/)

*[PostgreSQL Version 16+](https://www.postgresql.org/download/)

*[Git](https://git-scm.com/downloads)

## Core features
- Registration of a vehicle
- Display vehicles list
- Addition of a road and junctions
- Display lists of roads and junction
- See log of the vehicles in junction
- See the junction and congestion analysis
- Predict where congestion might appear

## Setup Instructions

### Step 1: Clone the Repository
Clone this repository to your local machine:

```bash
git clone https://github.com/Laurent-B2002/DigitalZooManagementSystem.git
cd AutomatedTrafficManagement
```

### Step 2: Run Migrations
Once inside the project directory, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Run the Program
Open a terminal in the project's directory and run:

```bash
python manage.py runserver
```

Then go to localhost:8000 in a webpage to access the program. Do note that in order to use your own database, the database settings in settings.py might need to be altered.
