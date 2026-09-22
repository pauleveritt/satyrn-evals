from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from models import Complaint, complaints

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


@app.get("/complaints")
async def complaints_board(request: Request):
    return templates.TemplateResponse(
        request, "complaints.html", {"complaints": complaints}
    )


@app.post("/complaints")
async def add_complaint(
    agent_name: Annotated[str, Form()],
    text: Annotated[str, Form()],
):
    complaints.append(Complaint(agent_name=agent_name, text=text))
    return RedirectResponse("/complaints")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", reload=True)
