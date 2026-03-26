from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import graph, chat
from app.services.neo4j_service import neo4j_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    neo4j_service.close()


app = FastAPI(
    title="Dodge AI - Graph Query Engine",
    description="SAP O2C data modeled as a graph with NL query interface",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health():
    try:
        neo4j_service.run_query("RETURN 1")
        return {"status": "healthy", "neo4j": "connected"}
    except Exception as e:
        return {"status": "degraded", "neo4j": str(e)}
