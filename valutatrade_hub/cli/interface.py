"""Содержит реализацию интерфейса взаимодействия с пользователем."""
import argparse # альтернатива shlex
from dataclasses import dataclass
from typing import Sequence

@dataclass
class Option:
    """Класс опции argparse.
    
    Args:
        name (str): название опции
        opt_format (list[str]): формат argparse
            пример ["-f", "--file"]
        opt_type (type): тип опции
        help_text (str): описание опции
    """
    name: str
    opt_format: list[str]
    opt_type: type
    help_text: str

class Command:
    def __init__(self, name: str, options: Sequence[Option], action):

class UserInterface:
    """Общий класс взаимодействия с пользователем"""
    
    def __init__(self): ...
    def start(self): ...
    def _handle_command