# TogetherWherever-Backend
This is a backend repository for TogetherWherever project.

# What is TogetherWherever
TogetherWherever is a web application integrated with AI that recommends places based on travelers' interests and companions (group-based recommendation), manages travel time, and ensures enjoyable experiences without missed schedules.

# How to run
1. First of all, you need to install the required packages using:
```
pip install -r requirements.txt
```
2. To run the app on local, use:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
3. Now, you can visit http://0.0.0.0:8000 and explore the API docs: http://0.0.0.0:8000/docs.
