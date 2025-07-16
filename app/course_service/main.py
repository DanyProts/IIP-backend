from fastapi import FastAPI
from .api import routes_course

app = FastAPI(title="Course Service")

# Include course routes
app.include_router(routes_course.course_router, prefix="/courses")
app.include_router(routes_course.content_router, prefix="/content")
app.include_router(routes_course.assignments_router, prefix="/assignments")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
