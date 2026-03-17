"""AWS Lambda handler for the FastAPI backend API."""
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
