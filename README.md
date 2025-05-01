# TogetherWherever-Backend
This is a backend repository for TogetherWherever project.

# What is TogetherWherever
TogetherWherever is a web application integrated with AI that recommends places based on travelers' interests and companions (group-based recommendation), manages travel time, and ensures enjoyable experiences without missed schedules.

# How to run
## Preparing the installation
1. Clone this repository into your machine.
```cmd
git clone https://github.com/TogetherWherever/TogetherWherever-Backend.git TogetherWherever-Backend
cd TogetherWherever-Backend
```
2. You need to set up the environment variables. You can do this by creating a `.env` file in the root directory.
Please refer to the `example.env` file to see the required environment variables.

## Run on Local
1. First of all, you need to install the required packages using:
```
pip install -r requirements.txt
``` 
2. Now, we will need to set up the database. You can do this by running the following command:
```
python -m app.database.create_db
```
3. To run the app on local, use:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
4. Now, you can visit http://0.0.0.0:8000 and explore the API docs: http://0.0.0.0:8000/docs.

## Run on Docker
1. You can simply build and start the applicastion by,
```cmd
docker compose up -d --build
```
2. Now, you can visit http://0.0.0.0:8000 and explore the API docs: http://0.0.0.0:8000/docs.
