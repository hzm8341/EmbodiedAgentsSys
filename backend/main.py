"""FastAPI 后端入口 - LLM 机器人控制"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router as routes_router
from backend.api import urdf, state, chat, ik, agent_ws, traces, auth
from backend.services.simulation import simulation_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    simulation_service.initialize()
    simulation_service.launch_viewer()
    yield
    simulation_service.close_viewer()


app = FastAPI(title="LLM Robot Control API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_router, prefix="/api")
app.include_router(urdf.router)
app.include_router(state.router)
app.include_router(chat.router, prefix="/api")
app.include_router(ik.router)
app.include_router(agent_ws.router)
app.include_router(traces.router)
app.include_router(auth.router)

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
