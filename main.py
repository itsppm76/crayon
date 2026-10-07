import logging
from dotenv import load_dotenv
from config.settings import Settings
from core.agent import Agent
from core.memory import InMemoryMemory
from core.model_router import ModelRouter
from adapters.telegram.bot import run

if __name__ == "__main__":
    load_dotenv(); logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings(); run(Agent(ModelRouter(settings), InMemoryMemory()), settings)
