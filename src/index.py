from src.storage.datatypes import Agenda, toAgenda
from src.exceptions import retry_on
from asyncio import run
from classeviva import *
from classeviva.eccezioni import ErroreHTTP404, ErroreHTTP

class API:
    def __init__(self):
        pass

    @classmethod
    @retry_on((ErroreHTTP404, ErroreHTTP), max_attempts=6)
    def getMyHomework(cls, username: str, password: str) -> Agenda:
        return toAgenda(run(Utente(username, password).agenda()))